# Product Requirements Document

Compliance-Driven Expense Reimbursement Application

Grounded in Chinese Financial and Accounting Regulations

| Field | Value |
| --- | --- |
| Document Title | Product Requirements Document - Compliance-Driven Expense Reimbursement Application |
| Version | 1.0 (Draft for Review) |
| Date | 2026-10-03 |
| Status | Draft |
| Owner | [TBD - Product Owner] |
| Authors | Drafted by Doubao; [TBD - Final Author] |
| Reviewers | Finance & Accounting; Compliance/Legal; Engineering; Product Management |
| Classification | Internal - Confidential |

## Revision History

| Version | Date | Author | Description of Change |
| --- | --- | --- | --- |
| 1.0 | 2026-10-03 | [TBD] | Initial draft covering the five regulatory bases and MVP-to-release roadmap. |

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Goals and Non-Goals](#2-goals-and-non-goals)
3. [Regulatory Compliance Framework](#3-regulatory-compliance-framework)
4. [Users and Personas](#4-users-and-personas)
5. [Core User Stories](#5-core-user-stories)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Data Requirements](#8-data-requirements)
9. [Acceptance Criteria (Key Compliance Scenarios)](#9-acceptance-criteria-key-compliance-scenarios)
10. [Edge Cases and Risk Mitigation](#10-edge-cases-and-risk-mitigation)
11. [Release Strategy](#11-release-strategy)
12. [Assumptions and Open Questions](#12-assumptions-and-open-questions)
13. [Appendix A - References](#13-appendix-a---references)

# 1. Executive Summary

Organizations operating in the People’s Republic of China must process employee
expense reimbursements in a way that complies with accounting law, invoice
administration rules, and regulations on the electronic handling of accounting
vouchers. Manual, paper-based reimbursement flows are slow and expose
organizations to material compliance risk: forged or altered invoices, duplicate
reimbursement of the same invoice, an absence of a trustworthy approval audit
trail, improper handling of electronic vouchers (for example archiving only a
screenshot instead of the original file), and unresolved questions about where
accounting data is stored and backed up.

This document defines the product requirements for a compliance-first expense
reimbursement application (the "App"). The App makes regulatory compliance an
inherent part of the reimbursement workflow rather than a post-hoc audit
exercise. It verifies the authenticity of every invoice, prevents duplicate
reimbursement and duplicate entry into the books, records an immutable and
tamper-evident approval trail, supports compliant electronic-only bookkeeping
and archiving with full metadata and original-file retention, parses the
official electronic-voucher accounting data standard, and enforces security,
backup, and data-residency requirements.

Five Chinese regulatory instruments form the compliance backbone of this
product. They are described in Section 3 and referenced throughout the functional
requirements (Section 6).

| # | Regulatory Instrument | Regulation Name (Chinese) | Primary Compliance Driver for the App |
| --- | --- | --- | --- |
| R1 | Accounting Law of the People’s Republic of China (2024 Amendment) | 《中华人民共和国会计法》 | Original vouchers must be authentic and legal; no forged or altered vouchers; accounting records must be complete and traceable. |
| R2 | Measures for the Administration of Invoices and its Implementation Rules | 《中华人民共和国发票管理办法》及其实施细则 | Digital e-invoices carry the same legal force as paper invoices; issuance of false invoices and acceptance of non-compliant invoices are prohibited. |
| R3 | Notice on Standardizing the Reimbursement, Bookkeeping and Archiving of Electronic Accounting Vouchers | 《关于规范电子会计凭证报销入账归档的通知》 | Under defined conditions electronic-only bookkeeping is allowed; the system must prevent duplicate entry, resist tampering, and preserve complete metadata and original files. |
| R4 | Accounting Informatization Work Standards (2024 Revision) | 《会计信息化工作规范》 | Systems must be adapted to the electronic-voucher accounting data standard; secure transmission/storage, accounting data backup, and in-country backup retention for cross-border deployments. |
| R5 | Electronic Voucher Accounting Data Standards | 《电子凭证会计数据标准》 | A unified structured standard for digital e-invoices, fiscal e-receipts, travel itinerary receipts, and more. |

# 2. Goals and Non-Goals

## 2.1 Goals

G1 - Guarantee authenticity and legality of original vouchers: every invoice is
verified against authoritative sources before reimbursement (发票验真).

G2 - Eliminate duplicate reimbursement and duplicate entry: the same invoice
cannot be reimbursed twice or posted to the books twice (重复报销校验 / 防重复入账).

G3 - Provide a complete, tamper-evident approval audit trail: every handling,
review, and approval step is recorded immutably and is traceable (审批留痕).

G4 - Enable compliant electronic-only bookkeeping and archiving: preserve full
metadata and original files (OFD/XML/PDF), never screenshots only (电子入账归档).

G5 - Parse structured electronic-voucher data: automatically consume and process
electronic vouchers in line with the official accounting data standard
(电子凭证会计数据标准).

G6 - Enforce security, backup, and data residency: protect data in transit and
at rest, back up accounting data, and retain an in-country copy when
infrastructure is overseas (安全、备份、跨境驻留).

## 2.2 Non-Goals

NG1 - The App is not a full general-ledger (GL) or accounting system; it hands
off to the organization’s ERP/accounting system for final posting.

NG2 - The App does not replace the national e-invoice verification platform or
perform tax filing.

NG3 - The App does not provide legal advice or issue regulatory/compliance
certifications.

NG4 - The App is not responsible for converting paper vouchers into legally
binding electronic originals beyond what regulation permits.

# 3. Regulatory Compliance Framework

## 3.1 Overview of the Five Regulatory Bases

| # | Regulation | Issuing Body | Document No. / Revision | Effective / Status |
| --- | --- | --- | --- | --- |
| R1 | Accounting Law (2024 Amendment) | Standing Committee of the National People’s Congress | 2024 Amendment | Published 2024-06-28; effective 2024-07-01; current |
| R2 | Measures for the Administration of Invoices + Implementation Rules | State Council; State Taxation Administration | 2023 Revision; STA Order No. 56 | Current |
| R3 | Notice on Standardizing the Reimbursement, Bookkeeping and Archiving of Electronic Accounting Vouchers | Ministry of Finance; National Archives Administration | Caikuai [2020] No. 6 | Current |
| R4 | Accounting Informatization Work Standards | Ministry of Finance | 2024 Revision | Effective 2025-01-01; current |
| R5 | Electronic Voucher Accounting Data Standards (incl. implementation notices) | Ministry of Finance; State Taxation Administration; others | Incl. Caikuai [2025] No. 9 | Current |

## 3.2 Compliance Mapping Matrix

The table below maps each regulatory requirement onto the concrete capability
the App must provide. Every capability in Section 6 traces back to at least one
row here.

| Ref | Regulatory Requirement (Summary) | App Capability / Module |
| --- | --- | --- |
| R1-a | Original vouchers must be authentic and legal; accounting personnel may refuse untrue or illegal original vouchers. | FR-01 Invoice authenticity verification. |
| R1-b | No forged or altered accounting vouchers; accounting data must be complete and traceable. | FR-01, FR-02, FR-03; tamper-evident storage. |
| R2-a | Digital e-invoices (incl. fully digitalized "shu dian piao" invoices) have the same legal force as paper invoices and must not be refused. | FR-01; FR-04; FR-05. |
| R2-b | Issuance of false invoices and acceptance of non-compliant invoices are prohibited. | FR-01 detects red-letter cancellation, void, and non-compliant invoices. |
| R3-a | Electronic-only bookkeeping is permitted when vouchers are verified, tamper-proof, fully readable with metadata, and processed with due approval controls. | FR-03, FR-04, FR-05. |
| R3-b | The system must prevent duplicate entry and preserve metadata; original electronic files must be retained (screenshots are insufficient). | FR-02, FR-04. |
| R4-a | Accounting information systems must be adapted to the electronic-voucher accounting data standard. | FR-05. |
| R4-b | Secure transmission/storage; accounting data backup; in-country backup retention for cross-border deployments. | FR-06. |
| R5-a | A unified structured standard for digital e-invoices, fiscal e-receipts, and travel itinerary receipts enables automated parsing, bookkeeping, and archiving. | FR-05. |

# 4. Users and Personas

| Persona | Role | Key Needs |
| --- | --- | --- |
| Employee / Claimant | Creates and submits expense reports with supporting vouchers. | Fast submission, immediate authenticity and duplicate feedback, clear status. |
| Manager / Approver | Reviews and approves or rejects reports under delegated authority. | At-a-glance evidence, policy checks, mobile approval, immutable record of decision. |
| Finance / Accounting Officer | Verifies, books, and archives vouchers; handles exceptions. | Structured data for posting, electronic-only archiving with metadata, exception handling. |
| Compliance / Auditor | Reviews trails, exports evidence, monitors controls. | Immutable audit logs, full metadata and original files, export in archive-compliant format. |
| System Administrator | Configures policies, roles, integrations, backups. | Central configuration, integration endpoints, backup and residency controls. |

# 5. Core User Stories

| ID | User Story |
| --- | --- |
| US-01 | As an employee, I submit an expense report and each invoice is automatically verified for authenticity and legality so that forged or altered vouchers are caught immediately. |
| US-02 | As an employee, I am alerted if an invoice has already been reimbursed or submitted, so that I cannot claim the same expense twice. |
| US-03 | As an approver, I review the evidence, policy checks, and prior history for each line item, and my decision is recorded immutably. |
| US-04 | As a finance officer, I book reimbursements using structured data and archive the original electronic files with full metadata, without printing paper. |
| US-05 | As an auditor, I retrieve the original voucher file, its metadata, the verification result, and the full approval trail at any time. |
| US-06 | As an administrator, I configure expense policies, approval routing, integrations, and backup/data-residency settings. |

# 6. Functional Requirements

Each requirement states the intended behavior and the business rules that
enforce the compliance obligations in Section 3. IDs prefixed FR- are traceable
to the compliance mapping matrix.

## 6.1 FR-01 Invoice Authenticity Verification (发票验真)

The App must verify the authenticity, legality, and current status of every
invoice or voucher before it can be included in a reimbursable expense.

- Integrate with an authoritative invoice verification channel (national
  invoice verification / 发票查验 service or a certified aggregator) to validate
  each invoice in near real time.
- Support fully digitalized e-invoices (数电票), VAT electronic invoices,
  electronic fiscal receipts, and paper invoices via OCR plus verification.
- Detect and block red-letter cancellation (红冲) and voided (作废) invoices,
  and flag invoices whose status changed after an earlier successful
  verification.
- Reject invoices that fail verification, are inconsistent with their structured
  data, or are otherwise non-compliant, supporting the prohibition on accepting
  non-compliant invoices.
- Persist for every verification the verification result, verifier/source,
  timestamp, and reference number as audit evidence.

Acceptance: a forged or altered invoice, a red-flushed or voided invoice, and a
non-compliant invoice are each rejected with a clear reason and logged.

## 6.2 FR-02 Duplicate Reimbursement Prevention (重复报销校验 / 防重复入账)

The App must prevent the same voucher from being reimbursed more than once and
from being posted to the books more than once.

- Compute a unique fingerprint for every voucher from stable fields (invoice
  code, number, amount, issue date, and the digital e-invoice unique identifier
  where available).
- Check each voucher against all historical reimbursements and all in-flight
  reports across departments, entities, and time periods.
- Block submission and flag the owning report when a duplicate is detected;
  surface the prior claim for review.
- Maintain a unique posting key that the accounting/ERP system enforces,
  preventing duplicate entry into the ledger (防重复入账).

Acceptance: the same invoice submitted in a second report is blocked with a
reference to the original claim; no duplicate posting key can be created.

## 6.3 FR-03 Approval Workflow and Audit Trail (审批留痕)

The App must route every reimbursement through the required handling, review,
and approval steps and record every action immutably, per the required approval
(审签) procedures.

- Support configurable multi-stage routing, e.g. claimant → direct manager →
  finance review → final approver, with delegation and escalation rules.
- Append to an immutable, tamper-evident audit log for each event: actor,
  action, timestamp, prior/new state, comments, and the evidence snapshot.
- Reject any attempt to alter or delete past log entries; version history is
  preserved for documents and decisions.

Acceptance: every action on a report is recorded with actor, time, state change,
and comments; the log is append-only and verifiable.

## 6.4 FR-04 Electronic-Only Bookkeeping and Archiving (电子入账归档)

When the conditions for electronic-only handling are met, the App must support
bookkeeping and archiving without paper, while preserving complete metadata and
original files.

- Support electronic-only reimbursement, bookkeeping, and archiving when the
  voucher is verified, transmission/storage is secure and tamper-evident, and
  all metadata is read fully.
- Preserve the complete metadata of every electronic voucher (see Section 8.2)
  and bind it to the voucher file.
- Retain the original electronic file: OFD/XML for fully digitalized e-invoices,
  the original PDF/OFD for e-invoices, travel itinerary receipts, and other
  voucher types. A screenshot is never sufficient.
- Detect and surface any alteration of the stored file (hash and integrity
  checks); store provenance and integrity evidence.
- Export vouchers and metadata in the formats required by accounting archive
  administration, and, where a paper printout is used as the record, retain the
  corresponding electronic voucher.

Acceptance: an electronic-only archived claim contains the original file(s) plus
full metadata with integrity evidence; no archived claim contains only a
screenshot.

## 6.5 FR-05 Structured Electronic-Voucher Data Parsing (电子凭证会计数据标准)

The App must consume the official electronic-voucher accounting data standard so
that voucher data can be parsed, validated, and posted automatically.

- Parse and validate structured data for supported voucher types: fully
  digitalized e-invoices (数电票), fiscal electronic receipts (财政电子票据),
  railway e-tickets and air travel itinerary receipts (行程单), bank e-receipts,
  and others as covered by the standard.
- Map parsed fields to the accounting line items and posting entries used by the
  organization’s ERP/accounting system.
- Flag inconsistencies between the structured data, the visual/layout file, and
  the verification result.
- Stay aligned with the phased upgrade requirement for accounting software to
  become fully adapted to the standard.

Acceptance: a supported digital voucher is parsed into correct structured
fields, validated, and mapped to posting entries without manual re-entry.

## 6.6 FR-06 Security, Backup, and Data Residency (安全、备份、跨境驻留)

The App must protect accounting data end to end and guarantee recoverability and
regulatory data placement.

- Encrypt data in transit (TLS) and at rest; apply role-based access control
  with least privilege and separation of duties.
- Provide tamper-evident integrity controls over vouchers, metadata, and audit
  logs.
- Automate accounting-data backup with configurable method, frequency, media,
  and retention; verify restorability.
- Where servers or backups are located outside China, maintain a copy of
  accounting data and backups within China (in-country data-residency
  retention).
- Record the deployment region and backup locations, and surface any
  configuration that would violate residency policy.

Acceptance: backup policy is enforced and restorable; any overseas deployment
retains a current in-country copy of accounting data and backups; residency
status is visible to administrators.

## 6.7 FR-07 Core Reimbursement Flow

The App must support the full reimbursement lifecycle from claim creation to
posting and payment hand-off.

- Create expense reports from vouchers and expense line items, with expense
  type, amount, currency, date, project/cost-center, and supporting evidence.
- Validate each line against the configured expense policy (limits, eligible
  categories, required approvals).
- Submit, approve/reject/return with comments, finance-verify, and hand off
  approved items for payment and posting.

Acceptance: a complete report can move through submission, approval,
verification, payment hand-off, and posting hand-off with full traceability.

## 6.8 FR-08 System Integration

- Invoice verification platform (national service or certified aggregator).
- Digital e-invoice / electronic-voucher source (e.g. the electronic invoice
  service platform).
- ERP / accounting / general-ledger system (posting hand-off with unique keys).
- Electronic archive system (voucher + metadata export and hand-off).
- Payment / treasury system and identity (SSO) and HR organizational data.

Acceptance: each integration is configurable, monitored, and logs both success
and failure for reconciliation.

## 6.9 FR-09 Notifications and Reminders

- Notify on pending approval, status changes, rejection with reason, and
  returned reports.
- Alert on red-letter cancellation, voided status change, or duplicate detection
  after initial verification.
- Remind on overdue approvals and incomplete evidence.

Acceptance: users and approvers receive timely, role-appropriate notifications;
critical compliance alerts are never suppressed.

## 6.10 FR-10 Administration and Configuration

- User, role, and permission management with separation of duties.
- Expense policy, approval routing, and delegation configuration.
- Integration endpoints, verification provider, and archive/ERP hand-off
  settings.
- Backup schedule and data-residency configuration; audit log export; retention
  settings.

Acceptance: an administrator can configure all of the above; changes are
themselves audit-logged.

# 7. Non-Functional Requirements

| Category | Requirement |
| --- | --- |
| Security | TLS 1.2+ for all transmissions; AES-256 (or equivalent) encryption at rest; role-based access control with least privilege; MFA for approvers; credentials never stored in plaintext; annual penetration testing. |
| Performance | Invoice verification result within 3 seconds at P95; report submission within 2 seconds; supports the organization’s peak daily reimbursement volume without degradation. |
| Availability | 99.9% monthly availability; defined RPO and RTO; redundant infrastructure for core verification and posting flows. |
| Auditability | Immutable, append-only audit logs; logs retained in line with applicable accounting archive requirements; exportable in a verifiable format. |
| Data retention | Vouchers, metadata, and audit logs retained per applicable accounting archive management rules (e.g. accounting vouchers for the statutory retention period). |
| Usability | Web and mobile access; guided submission with immediate compliance feedback; accessible design and bilingual (Chinese/English) support. |
| Scalability | Horizontal scaling for verification, archival, and backup workloads; multi-entity and multi-cost-center support. |

# 8. Data Requirements

## 8.1 Core Data Entities

| Entity | Description |
| --- | --- |
| User | Identity, role(s), department, cost center, approval authority. |
| Expense Report | Report header, status, workflow, totals, currency, submission data. |
| Expense Line Item | Voucher reference, expense type, amount, date, policy validation result. |
| Voucher / Invoice | Structured fields, original file reference, fingerprint, status (valid / red-flushed / voided / duplicate). |
| Verification Record | Verifier/source, result, timestamp, reference number. |
| Approval Task | Stage, actor, decision, comments, timestamp. |
| Audit Log Entry | Actor, action, timestamp, before/after state, evidence snapshot. |
| Archive Record | Original file, metadata bundle, integrity evidence, archive hand-off reference. |
| Backup Job | Schedule, scope, location, result, restoration verification. |

## 8.2 Metadata to Preserve for Electronic Vouchers

For every electronic voucher the App must preserve at least the following
metadata and bind it to the original file:

- Voucher type, issuing party/entity, and invoice or receipt code and number.
- Amount, tax amount, and currency; issue date and (where applicable) digital
  e-invoice unique identifier.
- File format and hash/integrity value of the original file.
- Received time, verification result and time, and the responsible actor.
- Posting reference (unique key) and archive hand-off reference.

## 8.3 Data Residency and Retention

Accounting data and backups are retained for the period required by applicable
accounting archive rules. Where infrastructure or backups reside outside China,
a current copy of accounting data and backups must be retained within China. All
retention and residency settings are visible to administrators and auditable.

# 9. Acceptance Criteria (Key Compliance Scenarios)

| ID | Scenario | Acceptance Result |
| --- | --- | --- |
| AC-01 | An employee submits a forged or altered invoice. | The App rejects it, logs the verification failure with reason, and notifies finance. |
| AC-02 | An invoice is red-letter cancelled (红冲) or voided. | The App detects the status and blocks reimbursement, alerting the claimant. |
| AC-03 | An invoice already reimbursed is submitted in a new report. | The App blocks it and shows the original claim reference. |
| AC-04 | A report is approved end to end. | Every handling/approval step is recorded in an immutable, tamper-evident audit log. |
| AC-05 | Finance archives an electronic-only claim. | The archive contains the original OFD/XML/PDF file(s) plus full metadata and integrity evidence; no screenshot-only claim is possible. |
| AC-06 | A supported digital voucher is submitted. | Structured data is parsed, validated, and mapped to posting entries without manual re-entry. |
| AC-07 | Overseas deployment is configured. | A current copy of accounting data and backups is retained within China; residency is visible to administrators. |
| AC-08 | An audit requests evidence. | Original file, metadata, verification result, and full approval trail are exportable in an archive-compliant format. |

# 10. Edge Cases and Risk Mitigation

| Risk / Edge Case | Mitigation |
| --- | --- |
| An invoice verifies initially but is later red-flushed or voided. | Periodic re-verification of high-value or archived invoices; alert finance and trigger reversal workflow. |
| External verification service is slow or unavailable. | Queue with retry and back-off; graceful degradation with manual review; status indicators for users. |
| Duplicate detection across merged entities or renamed suppliers. | Normalize and reconcile supplier identifiers; support a cross-entity duplicate fingerprint. |
| OCR errors on paper invoices. | Require human validation of OCR output before acceptance; retain the scanned image. |
| Overseas deployments without in-country copy. | Block or warn on configuration that violates data-residency policy; enforce in-country backup. |
| Data breach or integrity compromise. | Incident-response process, integrity alerting, rollback/restoration from verified backups, and regulatory reporting as applicable. |

# 11. Release Strategy

| Phase | Scope | Exit Criteria |
| --- | --- | --- |
| MVP | FR-01 invoice verification; FR-02 duplicate prevention; FR-03 approval & audit trail; FR-07 core flow. | Forged/duplicate/red-flushed invoices blocked; immutable audit trail in place for all approvals. |
| Phase 2 | FR-04 electronic-only bookkeeping & archiving; FR-05 structured data parsing. | Electronic-only archiving with original files + metadata; supported digital vouchers auto-parsed and mapped. |
| Phase 3 | FR-06 security/backup/residency hardening; FR-08 expanded integrations; FR-09 notifications; FR-10 administration. | Backup and residency controls enforced; integrations configurable and monitored; administration self-serve. |

# 12. Assumptions and Open Questions

## 12.1 Assumptions

- The App targets organizations subject to Chinese accounting and invoice
  administration rules and using the national electronic-voucher infrastructure.
- A certified invoice verification channel and the electronic invoice / digital
  e-invoice service are available for integration.
- The organization operates an ERP/accounting system that accepts posting
  hand-offs with unique keys.
- Deployment may be cloud or on-premise; if any component is hosted overseas, an
  in-country accounting-data copy will be maintained.

## 12.2 Open Questions

- [TBD] Which ERP/accounting system and which invoice-verification provider will
  be integrated?
- [TBD] Cloud, on-premise, or hybrid deployment, and in which region(s)?
- [TBD] Organization structure, approval authority matrix, and delegation rules.
- [TBD] Final sign-off on regulatory interpretation by the organization’s
  finance and legal teams.

# 13. Appendix A - References

The following regulatory instruments are the basis for the requirements in this
document. Official sources are listed for traceability.

| # | Regulation | Document No. / Revision | Issuing Body | Source |
| --- | --- | --- | --- | --- |
| R1 | Accounting Law of the People’s Republic of China (2024 Amendment) | 2024 Amendment | Standing Committee of the NPC | kjs.mof.gov.cn/zhengcefabu/202408/t20240812_3941615.htm |
| R2 | Measures for the Administration of Invoices; Implementation Rules | 2023 Revision; STA Order No. 56 | State Council; STA | xzfg.moj.gov.cn (LawID=1682); fgk.chinatax.gov.cn |
| R3 | Notice on Standardizing the Reimbursement, Bookkeeping and Archiving of Electronic Accounting Vouchers | Caikuai [2020] No. 6 | MOF; National Archives Administration | gov.cn/zhengce/zhengceku/2020-04/03/content_5498598.htm |
| R4 | Accounting Informatization Work Standards | 2024 Revision | Ministry of Finance | kjs.mof.gov.cn/zhengcefabu/202408/P020240805628932632907.pdf |
| R5 | Electronic Voucher Accounting Data Standards (incl. Caikuai [2025] No. 9) | Caikuai [2025] No. 9 | MOF; STA; other agencies | gov.cn/zhengce/202505/content_7024320.htm |
