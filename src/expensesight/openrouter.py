"""OpenRouter adapter for ExpenseSight's advisory semantic review.

The adapter performs one structured-output request per eligible claim. It
does not know about, or have permission to choose, the final business action.
"""
from __future__ import annotations

import json
import time
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .model_output import ModelReviewOutput, parse_model_review_output


OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-3.5-flash-lite"


class OpenRouterError(RuntimeError):
    """Raised when OpenRouter cannot provide a valid review response."""


@dataclass(frozen=True)
class ModelUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class OpenRouterReview:
    output: ModelReviewOutput
    raw_output: dict[str, Any]
    model: str
    response_id: str | None
    usage: ModelUsage


def _structured_output_schema(
    schema: dict[str, Any],
    warning_taxonomy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Prepare a provider-friendly strict schema with local references inlined."""
    cleaned = {
        key: value
        for key, value in schema.items()
        if key not in {"$schema", "$id", "title"}
    }
    definitions = cleaned.pop("$defs", {})

    def inline_local_refs(node: Any) -> Any:
        if isinstance(node, list):
            return [inline_local_refs(item) for item in node]
        if not isinstance(node, dict):
            return node
        reference = node.get("$ref")
        if reference == "#/$defs/material_facts":
            if "material_facts" not in definitions:
                raise ValueError("Schema is missing $defs.material_facts")
            return inline_local_refs(deepcopy(definitions["material_facts"]))
        return {key: inline_local_refs(value) for key, value in node.items()}

    prepared = inline_local_refs(cleaned)
    if warning_taxonomy is None:
        return prepared

    warning_items = prepared["properties"]["warnings"]["items"]
    all_fact_properties = warning_items["properties"]["facts"]["properties"]
    branches = []
    for contract in warning_taxonomy.get("codes", []):
        if contract.get("owner") not in {"semantic_model", "semantic_model_or_route_layer"}:
            continue
        fact_keys = list(contract.get("fact_keys", []))
        missing_schema_keys = set(fact_keys) - set(all_fact_properties)
        if missing_schema_keys:
            raise ValueError(
                f"Warning taxonomy facts are absent from the output schema: "
                f"{sorted(missing_schema_keys)}"
            )
        branch = deepcopy(warning_items)
        branch["properties"]["warning_code"] = {
            "type": "string",
            "enum": [contract["code"]],
        }
        branch["properties"]["facts"] = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                key: deepcopy(all_fact_properties[key]) for key in fact_keys
            },
            "required": fact_keys,
        }
        branch["properties"]["materiality"] = {
            "type": "string",
            "enum": [contract["materiality"]],
        }
        if "policy_clause" not in branch["required"]:
            branch["required"].append("policy_clause")
        branches.append(branch)

    if not branches:
        raise ValueError("Warning taxonomy has no semantic output contracts")
    prepared["properties"]["warnings"]["items"] = {"oneOf": branches}
    return prepared


def build_messages(
    *,
    system_prompt: str,
    request_template: str,
    policy_context: str,
    warning_taxonomy: dict[str, Any],
    deterministic_findings: list[dict[str, Any]],
    claim: dict[str, Any],
) -> list[dict[str, str]]:
    """Render the provider-neutral prompt files for one claim."""
    replacements = {
        "{{POLICY_CONTEXT}}": policy_context,
        "{{WARNING_TAXONOMY}}": json.dumps(warning_taxonomy, ensure_ascii=False, indent=2),
        "{{DETERMINISTIC_FINDINGS_JSON}}": json.dumps(
            deterministic_findings, ensure_ascii=False, indent=2
        ),
        "{{CLAIM_JSON}}": json.dumps(claim, ensure_ascii=False, indent=2),
    }
    request = request_template
    for marker, value in replacements.items():
        request = request.replace(marker, value)
    unresolved = [marker for marker in replacements if marker in request]
    if unresolved:
        raise ValueError(f"Prompt template has unresolved markers: {unresolved}")
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request},
    ]


class OpenRouterClient:
    """Minimal OpenRouter client with bounded retry and strict output parsing."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = 90.0,
        max_retries: int = 2,
    ) -> None:
        if not api_key.strip():
            raise ValueError("OPENROUTER_API_KEY is missing")
        self._api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def review(
        self,
        *,
        claim_id: str,
        messages: list[dict[str, str]],
        output_schema: dict[str, Any],
        warning_taxonomy: dict[str, Any] | None = None,
    ) -> OpenRouterReview:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 4096,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "expensesight_advisory_review",
                    "strict": True,
                    "schema": _structured_output_schema(output_schema, warning_taxonomy),
                },
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Title": "ExpenseSight course project",
        }

        response = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    OPENROUTER_CHAT_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                if attempt >= self.max_retries:
                    raise OpenRouterError(f"OpenRouter request failed: {type(exc).__name__}") from exc
                time.sleep(2**attempt)
                continue

            if response.status_code < 400:
                break
            if response.status_code != 429 and response.status_code < 500:
                raise OpenRouterError(
                    f"OpenRouter returned HTTP {response.status_code}: {response.text[:500]}"
                )
            if attempt >= self.max_retries:
                raise OpenRouterError(
                    f"OpenRouter returned HTTP {response.status_code} after retries: "
                    f"{response.text[:500]}"
                )
            retry_after = response.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else 2**attempt
            except ValueError:
                delay = 2**attempt
            time.sleep(min(delay, 30.0))

        if response is None:
            raise OpenRouterError("OpenRouter request produced no response")
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("message content is not text")
            raw_output = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError) as exc:
            raise OpenRouterError("OpenRouter response did not contain valid structured JSON") from exc

        parsed = parse_model_review_output(raw_output, expected_claim_id=claim_id)
        usage_raw = body.get("usage") or {}
        usage = ModelUsage(
            prompt_tokens=usage_raw.get("prompt_tokens"),
            completion_tokens=usage_raw.get("completion_tokens"),
            total_tokens=usage_raw.get("total_tokens"),
        )
        return OpenRouterReview(
            output=parsed,
            raw_output=raw_output,
            model=str(body.get("model") or self.model),
            response_id=body.get("id"),
            usage=usage,
        )


def load_review_assets(root: Path) -> dict[str, Any]:
    """Load prompts, policy, taxonomy, and schema from the repository."""
    return {
        "system_prompt": (root / "prompts" / "semantic_review_system.md").read_text(
            encoding="utf-8"
        ),
        "request_template": (root / "prompts" / "semantic_review_request.md").read_text(
            encoding="utf-8"
        ),
        "policy_context": (root / "data" / "policies" / "travel_policy.md").read_text(
            encoding="utf-8"
        ),
        "warning_taxonomy": json.loads(
            (root / "evals" / "warning_taxonomy.json").read_text(encoding="utf-8")
        ),
        "output_schema": json.loads(
            (root / "evals" / "schemas" / "model_review_output.schema.json").read_text(
                encoding="utf-8"
            )
        ),
    }
