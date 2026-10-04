"""Small deterministic parsers for pre-extracted attachment descriptions."""
from __future__ import annotations

import re


DOCUMENT_PATTERNS = (
    re.compile(r"(?:ticket\s*(?:no\.?|number)|票号)\s*[:：]?\s*([A-Z0-9-]+)", re.I),
    re.compile(r"(?:invoice\s*(?:no\.?|number)|发票号)\s*[:：]?\s*([A-Z0-9-]+)", re.I),
)

AMOUNT_PATTERNS = (
    re.compile(r"(?:fare|amount)\s*(?:RMB|CNY|¥)?\s*([0-9]+(?:\.[0-9]+)?)", re.I),
    re.compile(r"(?:票价|金额)(?:人民币)?\s*([0-9]+(?:\.[0-9]+)?)\s*元?", re.I),
)


def extract_document_ids(text: str) -> list[str]:
    values: list[str] = []
    for pattern in DOCUMENT_PATTERNS:
        values.extend(match.upper() for match in pattern.findall(text or ""))
    return values


def extract_document_amount(text: str) -> float | None:
    for pattern in AMOUNT_PATTERNS:
        match = pattern.search(text or "")
        if match:
            return float(match.group(1))
    return None
