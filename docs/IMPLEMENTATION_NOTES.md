# Implementation notes

This document summarizes **custom work completed on top of the Udacity Financial Services Agentic AI starter**. 

---

## 1. What changed vs starter code (high level)


| Area                                  | Starter state           | Implemented / customized                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------------------------- | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `**src/foundation_sar.py`**           | TODO scaffolding        | Full Pydantic models (`CustomerData`, `AccountData`, `TransactionData`, `CaseData`, `RiskAnalystOutput`, `ComplianceOfficerOutput`), CSV-oriented normalizers (pandas `NaN`, int `ssn_last_4`, optional transaction strings), sane transaction amount bounds, `DataLoader.create_case_from_data`, `**ExplainabilityLogger`** with structured `inputs`/`outputs`, JSON repair helpers (`repair_llm_json_text`, `json_loads_llm_candidate`), risk calibration constants + `risk_analyst_calibration_rubric()`, parse **fallback** outputs for degraded LLM parses, `**audit_session_timestamp_utc`**, `**audit_jsonl_path`**, `**filed_sar_json_path**` |
| `**src/risk_analyst_agent.py**`       | Skeleton                | Chain-of-Thought **system prompt** (five `reasoning_steps`, fixed classification/risk enums), OpenAI completion flow, JSON extract/validate, **retry** turn with correction prompt, **fallback** policy, `**json_recovery`** path in audit payloads, calibration aligned with `**RISK_LEVEL_CONFIDENCE_BANDS`**                                                                                                                                                                                                                                                                                                                                       |
| `**src/compliance_officer_agent.py**` | Skeleton                | ReACT-oriented **system prompt**, narrative generation + validation, `**_finalize_compliance_output_with_deterministic_qa`** (word limit, mandated terminology list, subject/suspicion/time/amount/rationale/citation echoes, `**key_indicator`** echo), JSON retry + `**compliance_officer_output_parse_fallback**`, audit payloads include `**risk_analysis**` snapshot in `**inputs**`                                                                                                                                                                                                                                                             |
| **Notebooks**                         | Partial / instructional | `**01_data_exploration`**: foundation smoke writes audit under `**outputs/audit_logs/`** with stamped names. `**02_agent_development**`: drives agents against real `**CaseData**`; audit logs routed under `**outputs/audit_logs/**` with `<stem>_run_<UTC>.jsonl`. `**03_workflow_integration**`: end-to-end screening → Risk → **human gate** (logged) → Compliance → SAR JSON; **session-scoped** audit path and **deterministic SAR filenames**; metrics / QA cells                                                                                                                                                                              |
| **Tests** (`tests/`)                  | Starter scaffolding     | Expanded `**test_foundation`**, `**test_risk_analyst`**, `**test_compliance_officer**` exercising schemas, loaders, mocks, retry/fallback, deterministic QA gates, logger shape (`**inputs`/`outputs**`, `**json_recovery.path**`)                                                                                                                                                                                                                                                                                                                                                                                                                    |
| **Docs / repo hygiene**               | Course README only      | This `**docs/`** tree; `**outputs/README.md`** conventions; `**images/System Architecture SAR.png**` referenced from root README                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |


---

## 2. Design choices worth calling out

- **Two-stage cost path**: Compliance / narrative generation runs only after a **human proceed** decision at the gate (workflow notebook), avoiding unnecessary narrative API calls on rejected cases (metrics section quantifies skipped second-stage volume).
- **Risk confidence calibration**: `**RiskAnalystOutput`** validates that `**confidence_score`** sits in a band that matches `**risk_level**` (rubrics embedded in prompts and enforced in schema).
- **Production-like resilience**: Both agents tolerate malformed LLM JSON via **repair → retry → validated fallback**, while **logging** records the recovery path (`outputs.json_recovery.path`: `direct` | `retry` | `fallback`).
- **Compliance narrative QA**: Beyond the LLM `**completeness_check`**, a **deterministic checker** rejects weak narratives so tests and demos don’t silently pass thin content.
- **Auditability**: Each JSONL line is a single JSON object with **nested structured** `inputs` and `outputs` (not Python `str(dict)` blobs), `**event_id`** per line, and explicit **human gate** rows (`HumanReviewer`, `human_gate_decision`).
- **Output hygiene**: Generated artifacts are confined to `**outputs/audit_logs/`** and `**outputs/filed_sars/`** with **UTC run timestamps** in names for traceability (see §4).

---

## 3. Audit logging schema (JSONL)

**Location:** configured per run, e.g. `outputs/audit_logs/<stem>_run_<YYYYMMDD_HHMMSS>.jsonl` (UTC). The workflow notebook prints the resolved path when initializing `**ExplainabilityLogger`**.

Each **line** is one JSON object:


| Field               | Type            | Notes                                                                                                            |
| ------------------- | --------------- | ---------------------------------------------------------------------------------------------------------------- |
| `event_id`          | string (UUID)   | Unique per append; distinguishes concurrent lines sharing `case_id`                                              |
| `timestamp`         | ISO-8601 string | UTC                                                                                                              |
| `case_id`           | string          | Case UUID from `**DataLoader`**                                                                                  |
| `agent_type`        | string          | Examples: `**DataLoader`**, `**RiskAnalyst**`, `**ComplianceOfficer**`, `**HumanReviewer**`                      |
| `action`            | string          | Examples: `**create_case**`, `**analyze_case**`, `**generate_narrative**`, `**human_gate_decision**`             |
| `inputs`            | object          | Structured context (counts, `**risk_analysis**` model snapshot for Compliance, full risk dump at gate—see below) |
| `outputs`           | object          | Structured result (risk/compliance payloads; `**decision**` at gate—see below)                                   |
| `reasoning`         | string          | Human-readable summary suitable for examiner notes                                                               |
| `execution_time_ms` | number          | Wall duration of the logged step                                                                                 |
| `success`           | boolean         |                                                                                                                  |
| `error_message`     | string or null  | Populated when `success` is false                                                                                |


**Risk Analyst successful row (typical `outputs`):** `classification`, `confidence_score`, `**reasoning_steps`**, `**key_indicators`**, `**risk_level**`, computed `**reasoning**` (where included in dump), `**json_recovery**`.

**Compliance Officer successful row (typical `inputs`):** `case_id`, `customer_id`, full `**risk_analysis`** (structured). `**outputs`**: narrative fields + `**json_recovery**`.

### Human gate event

Emitted from `**03_workflow_integration.ipynb**` when the reviewer answers the proceed prompt (`yes`/`no` or `**auto_approve**` in parametrized runs):


| `agent_type`    | `action`              |
| --------------- | --------------------- |
| `HumanReviewer` | `human_gate_decision` |


**Typical `inputs` keys:**  
`interaction_type` (`human_sar_filing_gate`), `stage_completed_before_decision`, `auto_approve`, `reviewer_prompt_response`, `**risk_analysis`** (full `**RiskAnalystOutput.model_dump(mode="json")`**).

**Typical `outputs` keys:**  
`decision`: `**PROCEED`** | `**REJECT`**; `**sar_filing_approved**` (boolean); `**next_stage**`; `**outcome_detail**` (e.g. `APPROVED_FOR_COMPLIANCE` / `REJECTED_AT_GATE`).

---

## 4. Output directory conventions

All generated SAR and audit artifacts are intended to live under the repo `**outputs/**` tree only (not under `**notebooks/**` or cwd litter).


| Kind           | Pattern                                                           | Helper (code)              |
| -------------- | ----------------------------------------------------------------- | -------------------------- |
| Audit JSONL    | `outputs/audit_logs/<stem>_run_<YYYYMMDD_HHMMSS>.jsonl`           | `audit_jsonl_path(...)`    |
| Filed SAR JSON | `outputs/filed_sars/<same_run_TS>__case_<case_id>__<sar_id>.json` | `filed_sar_json_path(...)` |


Notebook `**03**` binds one `**AUDIT_SESSION_TS**` for the session so every SAR filename in that run shares the **same timestamp prefix**, correlating disk files with the audit log stem chosen for `**ExplainabilityLogger`**.

Older committed samples may use legacy names (e.g. `SAR_<uuid>.json` only); prefer re-running `**03`** to produce the stamped filenames.

See also: `**outputs/README.md**`.

---

## 5. How to reproduce SARs, audit logs, and metrics

### 5.1 Environment

1. Python 3.10+ compatible with `**requirements.txt**`.
2. Copy `**.env.template**` → `**.env**`, set `**OPENAI_API_KEY**` to the Udacity Vocareum key (`**voc-…**`).
3. Install: `pip install -r requirements.txt`.
4. For `**03**`/`**02**` API paths, notebooks use Vocareum’s OpenAI base URL as configured (see notebook “OpenAI Setup” cells).

### 5.2 Validate implementation (no API required for most tests)

```bash
cd /path/to/agentic-ai-financial-compliance-sar
python -m pytest tests/ -q
```

Many tests mock the OpenAI client; a small subset may call the live API if enabled in your tree—run with network only when intended.

### 5.3 Generate audit logs + SAR JSON + printed metrics (full path)

1. Open `**notebooks/03_workflow_integration.ipynb**`.
2. **Run all cells from the top** in order (ensures `**project_root`**, `**OUTPUTS_DIR`**, `**AUDIT_SESSION_TS**`, `**AUDIT_LOG_PATH**`, and SAR helpers share one session).
3. At each **“Proceed with SAR filing?”** prompt, enter `**yes`** / `**y`** to file, or `**no**` to log a `**REJECT**` gate row and skip stage 2 for that customer.
4. After the workflow cell:
  - **Audit:** new lines in the printed `**AUDIT_LOG_PATH`** under `**outputs/audit_logs/`**.
  - **SARs:** JSON files under `**outputs/filed_sars/`** with the `**…__case_…__….json`** pattern.
5. **Metrics:** run the **“Workflow Metrics and Analysis”** cells (Step 5 in the notebook)—they consume `**processed_cases`**, `**approved_sars`**, `**rejected_cases**`, `**audit_decisions**` from the workflow run and print approval rates and cost-skip heuristics.

### 5.4 Agent-only development smoke (optional)

`**02_agent_development.ipynb**`: after creating `**case_data**`, risk/compliance smoke cells append to `**outputs/audit_logs/**` using the notebook’s shared `**NOTEBOOK_AGENT_DEV_AUDIT_TS**` for correlation within that session.

### 5.5 Data exploration smoke (optional)

`**01_data_exploration.ipynb**` Step 1 smoke test writes `**data_exploration_smoke_run_<timestamp>.jsonl**` under `**outputs/audit_logs/**`.

---

