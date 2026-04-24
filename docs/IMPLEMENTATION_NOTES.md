# Implementation Notes

This document summarizes the custom implementation work completed beyond the starter scaffold,
including logging schema, output conventions, and how to reproduce SAR/audit artifacts.

## Key Customizations (Overall)
- Implemented full Pydantic schemas in `src/foundation_sar.py` for Customer/Account/Transaction/Case data plus agent outputs.
- Built `DataLoader` with CSV normalization (NaN -> `None`, `ssn_last_4` normalization) and case construction rules.
- Added core validations for dates, balances, transaction amount sanity checks, and 5-step Chain-of-Thought reasoning.
- Implemented `ExplainabilityLogger` with structured JSONL output, event IDs, and human-gate logging.
- Built Risk Analyst and Compliance Officer agents with structured prompts, JSON parsing, retries, and fallback outputs.
- Added deterministic compliance checks for narrative completeness, citations, and terminology enforcement.
- Integrated a widget-based human decision gate in `notebooks/03_workflow_integration.ipynb`.
- Added test coverage for schema validation, classification coverage, and end-to-end CSV integration.

## File Map (What to Review)
- `src/foundation_sar.py`: schemas, validation, `ExplainabilityLogger`, `DataLoader`.
- `src/risk_analyst_agent.py`: Chain-of-Thought prompt, JSON parsing, retries + fallback.
- `src/compliance_officer_agent.py`: ReACT prompt, narrative validation, retries + fallback.
- `notebooks/03_workflow_integration.ipynb`: end-to-end workflow + human gate UI.
- `tests/`: schema + agent tests and CSV integration coverage.

## Audit Logging Schema
Audit entries are JSONL records written by `ExplainabilityLogger`. Each entry includes:
- `event_id`: unique UUID per event
- `timestamp`, `case_id`, `agent_type`, `action`
- `input_data`, `output_data`: structured JSON payloads
- `input_summary`, `output_summary`: string summaries for quick review
- `reasoning`, `execution_time_ms`, `success`, `error_message`

Human gate events are logged with:
- `agent_type`: `HumanReviewer`
- `action`: `decision_gate`
- `output_data`: `decision`, `reviewer_input`, `reviewer_reason`

## Human-in-the-Loop Gate
- Notebook uses `ipywidgets` for approve/reject + optional rationale.
- Falls back to validated `input()` loop when widgets are unavailable.
- Decision and reason are logged via `ExplainabilityLogger`.

## Output Directory Conventions
- `outputs/audit_logs/`: all JSONL audit logs (timestamped file names)
- `outputs/filed_sars/`: generated SAR JSON documents

The workflow notebook writes logs as:
`outputs/audit_logs/workflow_integration_YYYYMMDD_HHMMSS.jsonl`

## Reproducing SARs and Audit Logs
1. Open `notebooks/03_workflow_integration.ipynb`.
2. Run the notebook cells in order.
3. When prompted, approve/reject in the widget or console prompt.
4. SARs are saved under `outputs/filed_sars/`.
5. Audit logs are saved under `outputs/audit_logs/`.

## SAR Document Contents
Generated SAR JSONs include:
- `sar_metadata` (sar_id, filing_date, review_status)
- `subject_information` (customer identifiers and risk rating)
- `suspicious_activity` (classification, risk_level, confidence, narrative, indicators)
- `regulatory_compliance` (citations, word count, compliance status)
- `audit_trail` (case_id, agents used, reviewer decision)

## Validation Rules (Summary)
- Dates must be `YYYY-MM-DD`.
- Monetary amounts must be finite, non-zero, and within a safe max range.
- Risk Analyst reasoning must be 5 labeled steps (`Step 1`…`Step 5`).
- Compliance narratives must be <=120 words and include required elements and citations.

## Metrics and Validation
- Workflow efficiency metrics are computed in the notebook after processing cases.
- CSV schema validation can be run via `pytest tests/test_foundation.py`.
- Agent tests run via `pytest tests/test_risk_analyst.py` and `pytest tests/test_compliance_officer.py`.

## Quick Test Commands
- `pytest tests/test_foundation.py`
- `pytest tests/test_risk_analyst.py`
- `pytest tests/test_compliance_officer.py`
