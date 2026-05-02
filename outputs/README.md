# Output Directories

All generated regulatory artifacts live under **`outputs/`** only. Do not write JSONL audit files or SAR JSON to `notebooks/` or the repo root.

## Naming convention

- **Audit JSONL** — `outputs/audit_logs/<notebook_or_flow>_run_<YYYYMMDD_HHMMSS>.jsonl` (UTC wall time, one file per notebook session / run).
- **Filed SAR JSON** — `outputs/filed_sars/<same_run_timestamp>__case_<case_id>__<sar_id>.json` so each file is traceable to a run and case.

Legacy ad-hoc names (e.g. fixed `workflow_integration.jsonl` with no timestamp) are superseded by the pattern above; re-run the workflow notebook to produce new files.

## 📄 filed_sars/
Generated SAR documents in JSON format. Each SAR includes:
- Customer information
- Transaction details
- Risk analysis results
- Compliance narrative
- Regulatory citations
- Audit trail references

## 📊 audit_logs/
Each line is one JSON object suitable for regulatory tooling. Fields include:

- `inputs` / `outputs` — structured JSON (not stringified blobs) for what went in and out of each step  
- Human SAR gate: `agent_type` **`HumanReviewer`**, `action` **`human_gate_decision`**, `outputs.decision` **`PROCEED`** or **`REJECT`**, with full `risk_analysis` under `inputs`  
- Agent rows: `RiskAnalyst` / `ComplianceOfficer` / `DataLoader` with CoT / narrative payloads in `outputs`

Also: `reasoning`, timestamps, `success` / `error_message`, and unique `event_id` per line.

Re-run **`notebooks/03_workflow_integration.ipynb`** (from the top) to append a new `workflow_integration_run_<timestamp>.jsonl` with human-gate rows if you need fresh samples in the repo.

These outputs demonstrate explainability and auditability for financial crime detection workflows.
