# Foundation SAR - Core Data Schemas and Utilities
# TODO: Implement core Pydantic schemas and data processing utilities

"""
This module contains the foundational components for SAR processing:

1. Pydantic Data Schemas:
   - CustomerData: Customer profile information
   - AccountData: Account details and balances  
   - TransactionData: Individual transaction records
   - CaseData: Unified case combining all data sources
   - RiskAnalystOutput: Risk analysis results
   - ComplianceOfficerOutput: Compliance narrative results

2. Utility Classes:
   - ExplainabilityLogger: Audit trail logging
   - DataLoader: Combines fragmented data into case objects

YOUR TASKS:
- Study the data files in data/ folder
- Design Pydantic schemas that match the CSV structure
- Implement validation rules for financial data
- Create a DataLoader that builds unified case objects
- Add proper error handling and logging
"""

import json
import math
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Literal, Tuple

import pandas as pd
import uuid
import os
from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


def repair_llm_json_text(raw: str) -> str:
    """Normalize smart quotes and strip trailing commas before `}`/`]` (limited LLM JSON repair)."""
    s = raw.strip()
    replacements = (
        ("\u201c", '"'),
        ("\u201d", '"'),
        ("\u2033", '"'),
        ("\u2032", "'"),
        ("\u2019", "'"),
    )
    for old, new in replacements:
        s = s.replace(old, new)

    trailing_comma_pat = re.compile(r",(\s*[}\]])")
    for _ in range(16):
        s2 = trailing_comma_pat.sub(r"\1", s)
        if s2 == s:
            break
        s = s2
    return s


def json_loads_llm_candidate(raw: str) -> Dict[str, Any]:
    """Parse JSON object text from an LLM; retry once after `repair_llm_json_text`."""
    last_err: Optional[json.JSONDecodeError] = None
    variants = [raw]
    repaired = repair_llm_json_text(raw)
    if repaired != raw:
        variants.append(repaired)
    for candidate in variants:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_err = exc
    assert last_err is not None
    raise last_err


def _is_na_scalar(value: Any) -> bool:
    """True for None, float NaN, pandas NA/NaN (not plain strings)."""
    if value is None:
        return True
    if isinstance(value, float) and value != value:  # NaN
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _normalize_ssn_last_4(value: Any) -> str:
    """Coerce pandas/numeric SSN fragments to a 4-digit string for validation."""
    if _is_na_scalar(value):
        raise ValueError("ssn_last_4 is required")
    if isinstance(value, bool):
        digits = str(value).strip()
    elif isinstance(value, (int, float)):
        digits = str(int(float(value)))
    else:
        digits = str(value).strip()
    if len(digits) > 4 and digits.isdigit():
        digits = digits[-4:]
    elif len(digits) < 4 and digits.isdigit():
        digits = digits.zfill(4)
    return digits


def _normalize_customer_row(data: Dict[str, Any]) -> Dict[str, Any]:
    """Align pandas CSV row dicts with CustomerData (int SSN, NaN optional fields)."""
    out = dict(data)
    if "ssn_last_4" in out:
        out["ssn_last_4"] = _normalize_ssn_last_4(out["ssn_last_4"])
    for key in ("phone", "occupation"):
        if key in out and _is_na_scalar(out[key]):
            out[key] = None
    if "annual_income" in out and _is_na_scalar(out["annual_income"]):
        out["annual_income"] = None
    return out


def _normalize_transaction_row(data: Dict[str, Any]) -> Dict[str, Any]:
    """Align pandas CSV row dicts with TransactionData optional strings."""
    out = dict(data)
    for key in ("counterparty", "location"):
        if key in out and _is_na_scalar(out[key]):
            out[key] = None
    return out


# Single-transaction magnitude bounds (signed amounts for debits/withdrawals).
_TRANSACTION_AMOUNT_ABS_MIN = 0.01
_TRANSACTION_AMOUNT_ABS_MAX = 50_000_000.0


# ===== TODO: IMPLEMENT PYDANTIC SCHEMAS =====

class CustomerData(BaseModel):
    """Customer information schema with validation
    
    REQUIRED FIELDS (examine data/customers.csv):
    - customer_id: str = Unique identifier like "CUST_0001"
    - name: str = Full customer name like "John Smith"
    - date_of_birth: str = Date in YYYY-MM-DD format like "1985-03-15"
    - ssn_last_4: str = Last 4 digits like "1234"
    - address: str = Full address like "123 Main St, City, ST 12345"
    - customer_since: str = Date in YYYY-MM-DD format like "2010-01-15"
    - risk_rating: Literal['Low', 'Medium', 'High'] = Risk assessment
    
    OPTIONAL FIELDS:
    - phone: Optional[str] = Phone number like "555-123-4567"
    - occupation: Optional[str] = Job title like "Software Engineer"
    - annual_income: Optional[int] = Yearly income like 75000
    
    HINT: Use Field(..., description="...") for required fields
    HINT: Use Field(None, description="...") for optional fields
    HINT: Use Literal type for risk_rating to restrict values
    """
    customer_id: str = Field(..., description="Unique customer identifier")
    name: str = Field(..., description="Full customer name")
    date_of_birth: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    ssn_last_4: str = Field(..., description="Last 4 digits of SSN only")
    address: str = Field(..., description="Full address")
    customer_since: str = Field(..., description="Customer since date in YYYY-MM-DD format")
    risk_rating: Literal["Low", "Medium", "High"] = Field(
        ..., description="Risk assessment rating"
    )
    phone: Optional[str] = Field(None, description="Phone number")
    occupation: Optional[str] = Field(None, description="Occupation")
    annual_income: Optional[int] = Field(None, description="Annual income")

    @model_validator(mode="before")
    @classmethod
    def _coerce_pandas_csv_types(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return _normalize_customer_row(data)
        return data

    @field_validator("date_of_birth", "customer_since")
    @classmethod
    def validate_date_format(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_validator("ssn_last_4")
    @classmethod
    def validate_ssn_last_4(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 4:
            raise ValueError("ssn_last_4 must be 4 digits")
        return value

class AccountData(BaseModel):
    """Account information schema with validation
    
    REQUIRED FIELDS (examine data/accounts.csv):
    - account_id: str = Unique identifier like "CUST_0001_ACC_1"
    - customer_id: str = Must match CustomerData.customer_id
    - account_type: str = Type like "Checking", "Savings", "Money_Market"
    - opening_date: str = Date in YYYY-MM-DD format
    - current_balance: float = Current balance (can be negative)
    - average_monthly_balance: float = Average balance
    - status: str = Status like "Active", "Closed", "Suspended"
    
    HINT: All fields are required for account data
    HINT: Use float for monetary amounts
    HINT: current_balance can be negative for overdrafts
    """
    account_id: str = Field(..., description="Unique account identifier")
    customer_id: str = Field(..., description="Customer identifier")
    account_type: str = Field(..., description="Account type")
    opening_date: str = Field(..., description="Opening date in YYYY-MM-DD format")
    current_balance: float = Field(..., description="Current account balance")
    average_monthly_balance: float = Field(..., description="Average monthly balance")
    status: Literal["Active", "Closed", "Suspended"] = Field(
        ..., description="Account status"
    )

    @field_validator("opening_date")
    @classmethod
    def validate_opening_date(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_validator("average_monthly_balance")
    @classmethod
    def validate_average_balance(cls, value: float) -> float:
        if value < 0:
            raise ValueError("average_monthly_balance cannot be negative")
        return value

class TransactionData(BaseModel):
    """Transaction information schema with validation
    
    REQUIRED FIELDS (examine data/transactions.csv):
    - transaction_id: str = Unique identifier like "TXN_B24455F3"
    - account_id: str = Must match AccountData.account_id
    - transaction_date: str = Date in YYYY-MM-DD format
    - transaction_type: str = Type like "Cash_Deposit", "Wire_Transfer"
    - amount: float = Transaction amount (negative for withdrawals)
    - description: str = Description like "Cash deposit at branch"
    - method: str = Method like "Wire", "ACH", "ATM", "Teller"
    
    OPTIONAL FIELDS:
    - counterparty: Optional[str] = Other party in transaction
    - location: Optional[str] = Transaction location or branch
    
    HINT: amount can be negative for debits/withdrawals
    HINT: Use descriptive field descriptions for clarity
    """
    transaction_id: str = Field(..., description="Unique transaction identifier")
    account_id: str = Field(..., description="Account identifier")
    transaction_date: str = Field(..., description="Transaction date in YYYY-MM-DD format")
    transaction_type: str = Field(..., description="Transaction type")
    amount: float = Field(..., description="Transaction amount (negative for debits)")
    description: str = Field(..., description="Transaction description")
    method: str = Field(..., description="Transaction method")
    counterparty: Optional[str] = Field(None, description="Transaction counterparty")
    location: Optional[str] = Field(None, description="Transaction location")

    @model_validator(mode="before")
    @classmethod
    def _coerce_pandas_csv_types(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return _normalize_transaction_row(data)
        return data

    @field_validator("transaction_date")
    @classmethod
    def validate_transaction_date(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount_range(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("amount must be a finite number (not NaN or infinite)")
        mag = abs(value)
        if mag < _TRANSACTION_AMOUNT_ABS_MIN:
            raise ValueError(
                f"amount absolute value must be at least {_TRANSACTION_AMOUNT_ABS_MIN}"
            )
        if mag > _TRANSACTION_AMOUNT_ABS_MAX:
            raise ValueError(
                f"amount absolute value must not exceed {_TRANSACTION_AMOUNT_ABS_MAX:,.0f}"
            )
        return value

class CaseData(BaseModel):
    """Unified case object combining all data sources
    
    REQUIRED FIELDS:
    - case_id: str = Unique case identifier (generate with uuid)
    - customer: CustomerData = Customer information object
    - accounts: List[AccountData] = List of customer's accounts
    - transactions: List[TransactionData] = List of suspicious transactions
    - case_created_at: str = ISO timestamp when case was created
    - data_sources: Dict[str, str] = Source tracking with keys like:
      * "customer_source": "csv_extract_20241219"
      * "account_source": "csv_extract_20241219" 
      * "transaction_source": "csv_extract_20241219"
    
    VALIDATION RULES:
    - transactions list cannot be empty (use @field_validator)
    - All accounts should belong to the same customer
    - All transactions should belong to accounts in the case
    
    HINT: Use @field_validator('transactions') with @classmethod decorator
    HINT: Check if not v: raise ValueError("message") for empty validation
    """
    case_id: str = Field(..., description="Unique case identifier")
    customer: CustomerData = Field(..., description="Customer data")
    accounts: List[AccountData] = Field(..., description="Customer accounts")
    transactions: List[TransactionData] = Field(..., description="Customer transactions")
    case_created_at: str = Field(..., description="Case creation timestamp")
    data_sources: Dict[str, str] = Field(..., description="Data source tracking")

    @field_validator("transactions")
    @classmethod
    def validate_transactions_not_empty(
        cls, value: List[TransactionData]
    ) -> List[TransactionData]:
        if not value:
            raise ValueError("transactions list cannot be empty")
        return value

    @field_validator("case_created_at")
    @classmethod
    def validate_case_created_at(cls, value: str) -> str:
        datetime.fromisoformat(value)
        return value

    @field_validator("accounts")
    @classmethod
    def validate_accounts_not_empty(
        cls, value: List[AccountData]
    ) -> List[AccountData]:
        if value is None:
            raise ValueError("accounts list cannot be None")
        return value

    @field_validator("data_sources")
    @classmethod
    def validate_data_sources(cls, value: Dict[str, str]) -> Dict[str, str]:
        if not value:
            raise ValueError("data_sources must include at least one source")
        return value

    @field_validator("accounts", mode="after")
    @classmethod
    def validate_accounts_customer_match(cls, value: List[AccountData], info):
        customer = info.data.get("customer")
        if customer and value:
            for account in value:
                if account.customer_id != customer.customer_id:
                    raise ValueError("account customer_id must match case customer_id")
        return value

    @field_validator("transactions", mode="after")
    @classmethod
    def validate_transactions_account_match(cls, value: List[TransactionData], info):
        accounts = info.data.get("accounts") or []
        account_ids = {account.account_id for account in accounts}
        for transaction in value:
            if account_ids and transaction.account_id not in account_ids:
                raise ValueError("transaction account_id must match case accounts")
        return value


# --- Risk Analyst: confidence ↔ risk_level calibration (schema + prompt; keep in sync) ---
RISK_LEVEL_CONFIDENCE_BANDS: Dict[str, Tuple[float, float]] = {
    "Low": (0.0, 0.48),
    "Medium": (0.40, 0.68),
    "High": (0.62, 0.88),
    "Critical": (0.82, 1.0),
}


def risk_analyst_calibration_rubric() -> str:
    """Human-readable rubric appended to the Risk Analyst system prompt."""
    lines = [
        "Confidence ↔ risk_level calibration (mandatory): choose risk_level first, then set "
        "confidence_score inside the matching inclusive band. Step 4 must justify the pair.",
    ]
    for level, (lo, hi) in RISK_LEVEL_CONFIDENCE_BANDS.items():
        lines.append(f"  • {level}: confidence_score between {lo} and {hi} (inclusive).")
    lines.append(
        "If evidence is ambiguous, prefer a lower risk_level or a confidence near the middle of its band."
    )
    return "\n".join(lines)


class RiskAnalystOutput(BaseModel):
    """Risk Analyst agent structured output
    
    REQUIRED FIELDS (for Chain-of-Thought agent output):
    - classification: Literal['Structuring', 'Sanctions', 'Fraud', 'Money_Laundering', 'Other']
    - confidence_score: float = Confidence between 0.0 and 1.0 (use ge=0.0, le=1.0)
    - reasoning_steps: List[str], exactly five non-empty strings (one per framework step)
    - key_indicators: List[str] = List of suspicious indicators found
    - risk_level: Literal['Low', 'Medium', 'High', 'Critical'] = Risk assessment

    reasoning (computed): compact text for SAR metadata / downstream prompts (≤500 chars)
    """

    classification: Literal[
        "Structuring", "Sanctions", "Fraud", "Money_Laundering", "Other"
    ] = Field(..., description="Suspicious activity classification")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )
    reasoning_steps: List[str] = Field(
        ...,
        min_length=5,
        max_length=5,
        description=(
            "Five Chain-of-Thought steps: "
            "(1) Data Review, (2) Pattern Recognition, "
            "(3) Regulatory Mapping, (4) Risk Quantification, "
            "(5) Classification Decision."
        ),
    )
    key_indicators: List[str] = Field(..., description="Key suspicious indicators")
    risk_level: Literal["Low", "Medium", "High", "Critical"] = Field(
        ..., description="Overall risk level"
    )

    @field_validator("reasoning_steps")
    @classmethod
    def validate_reasoning_steps(cls, steps: List[str]) -> List[str]:
        stripped = [s.strip() for s in steps]
        if any(len(s) == 0 for s in stripped):
            raise ValueError("Each reasoning_steps entry must be non-empty")
        max_each = 400
        if any(len(s) > max_each for s in stripped):
            raise ValueError(f"Each reasoning_steps entry must be at most {max_each} chars")
        return stripped

    @model_validator(mode="after")
    def validate_confidence_risk_calibration(self) -> "RiskAnalystOutput":
        lo, hi = RISK_LEVEL_CONFIDENCE_BANDS[self.risk_level]
        c = self.confidence_score
        if c < lo - 1e-9 or c > hi + 1e-9:
            raise ValueError(
                f"confidence_score ({c}) incompatible with risk_level {self.risk_level!r}: "
                f"expected between {lo} and {hi} inclusive (see risk_analyst_calibration_rubric)."
            )
        return self

    @computed_field
    @property
    def reasoning(self) -> str:
        lines = [
            f"Step {i}: {text}" for i, text in enumerate(self.reasoning_steps, start=1)
        ]
        blob = "\n".join(lines)
        if len(blob) <= 500:
            return blob
        return blob[:497] + "..."

class ComplianceOfficerOutput(BaseModel):
    """Compliance Officer agent structured output
    
    REQUIRED FIELDS (for ReACT agent output):
    - narrative: str = Regulatory narrative text (max 1000 chars for ≤200 words)
    - narrative_reasoning: str = Reasoning for narrative construction (max 500 chars)
    - regulatory_citations: List[str] = List of relevant regulations like:
      * "31 CFR 1020.320 (BSA)"
      * "12 CFR 21.11 (SAR Filing)"
      * "FinCEN SAR Instructions"
    - completeness_check: bool = Whether narrative meets all requirements
    
    HINT: Use Field(..., max_length=1000) for narrative length limit
    HINT: Use Field(..., max_length=500) for reasoning length limit
    HINT: Use bool type for completeness_check
    """
    narrative: str = Field(..., max_length=1000, description="Regulatory narrative")
    narrative_reasoning: str = Field(
        ..., max_length=500, description="Reasoning for narrative construction"
    )
    regulatory_citations: List[str] = Field(
        ..., description="List of relevant regulatory citations"
    )
    completeness_check: bool = Field(..., description="Whether narrative is complete")


def risk_analyst_output_parse_fallback(case_id: str) -> RiskAnalystOutput:
    """Conservative degraded output after JSON/schema recovery fails (audit-safe, in-band calibration)."""
    return RiskAnalystOutput(
        classification="Other",
        confidence_score=0.42,
        reasoning_steps=[
            "Data Review: Automated review halted before model output could be ingested reliably.",
            "Pattern Recognition: No additional typology tagging applied pending human validation.",
            "Regulatory Mapping: Case retained for SAR workflow with escalation per internal policy.",
            "Risk Quantification: Low calibrated confidence reflecting parser failure rather than substantive absolution.",
            "Classification Decision: Other with parsing_failed indicators for manual adjudication.",
        ],
        key_indicators=["parsing_failed", "manual_review_required"],
        risk_level="Low",
    )


def compliance_officer_output_parse_fallback(
    case_id: str, customer_name: str
) -> ComplianceOfficerOutput:
    """Placeholder narrative when LLM JSON cannot be validated; preserves downstream execution."""
    short = customer_name.strip() or "the subject customer"
    narrative = (
        f"Automated SAR narrative unavailable for case {case_id} ({short}). "
        "Summary of suspicious activity could not be machine-validated after JSON/schema recovery attempts. "
        "Prepare narrative manually under Bank Secrecy Act and FinCEN SAR instructions (parsing_failed)."
    )
    return ComplianceOfficerOutput(
        narrative=narrative,
        narrative_reasoning=(
            "Fallback response after Compliance Officer JSON parse or schema validation failure; completeness_check false."
        ),
        regulatory_citations=["FinCEN SAR Instructions"],
        completeness_check=False,
    )


def _audit_json_safe(value: Any) -> Any:
    """Recursively coerce values so each JSONL row is plain JSON (no Python repr blobs)."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return value
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, val in value.items():
            out[str(key)] = _audit_json_safe(val)
        return out
    if isinstance(value, (list, tuple)):
        return [_audit_json_safe(item) for item in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, BaseModel):
        return _audit_json_safe(value.model_dump(mode="json"))
    return str(value)


def audit_session_timestamp_utc() -> str:
    """UTC timestamp for deterministic output filenames (``YYYYMMDD_HHMMSS``)."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _filename_safe_fragment(value: str, max_length: int = 180) -> str:
    pieces: List[str] = []
    for char in value.strip():
        if char.isalnum() or char in "-_.":
            pieces.append(char)
        elif char.isspace():
            pieces.append("_")
    out = "".join(pieces).strip("._") or "unknown"
    return out[:max_length]


def audit_jsonl_path(
    project_outputs_dir: str, *, stem: str, session_timestamp_utc: str
) -> str:
    """Return ``.../outputs/audit_logs/<stem>_run_<UTC>.jsonl`` and ensure the directory exists."""
    audit_dir = os.path.join(project_outputs_dir, "audit_logs")
    os.makedirs(audit_dir, exist_ok=True)
    basename = f"{stem}_run_{session_timestamp_utc}.jsonl"
    return os.path.join(audit_dir, basename)


def filed_sar_json_path(
    project_outputs_dir: str,
    *,
    session_timestamp_utc: str,
    case_id: str,
    sar_id: str,
) -> str:
    """Return ``.../outputs/filed_sars/<UTC>__case_<id>__<sar_id>.json`` and ensure the directory exists."""
    sars_dir = os.path.join(project_outputs_dir, "filed_sars")
    os.makedirs(sars_dir, exist_ok=True)
    case_frag = _filename_safe_fragment(case_id)
    sar_frag = _filename_safe_fragment(sar_id)
    basename = f"{session_timestamp_utc}__case_{case_frag}__{sar_frag}.json"
    return os.path.join(sars_dir, basename)


# ===== TODO: IMPLEMENT AUDIT LOGGING =====

class ExplainabilityLogger:
    """Simple audit logging for compliance trails

    ATTRIBUTES:
    - log_file: str = Path to JSONL log file (default: "sar_audit.jsonl")
    - entries: List = In-memory storage of log entries

    METHODS:
    - log_agent_action(): Logs agent actions with structured data

    LOG ENTRY STRUCTURE (JSON-serializable; suitable for regulatory tooling):
    {
        'event_id': str(uuid.uuid4()),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'case_id': case_id,
        'agent_type': agent_type,
        'action': action,
        'inputs': { ... },   # structured input payload (nested JSON objects)
        'outputs': { ... },  # structured output payload
        'reasoning': reasoning,
        'execution_time_ms': execution_time_ms,
        'success': success,
        'error_message': error_message | null
    }
    """

    def __init__(self, log_file: str = "sar_audit.jsonl"):
        self.log_file = log_file
        self.entries: List[Dict[str, Any]] = []

    def log_agent_action(
        self,
        agent_type: str,
        action: str,
        case_id: str,
        input_data: Dict,
        output_data: Dict,
        reasoning: str,
        execution_time_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """Append one audit event; ``inputs``/``outputs`` are nested JSON objects, not string summaries."""
        entry = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "case_id": case_id,
            "agent_type": agent_type,
            "action": action,
            "inputs": _audit_json_safe(input_data),
            "outputs": _audit_json_safe(output_data),
            "reasoning": reasoning,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "error_message": error_message,
        }
        self.entries.append(entry)
        with open(self.log_file, "a", encoding="utf-8") as log_handle:
            log_handle.write(json.dumps(entry) + "\n")

# ===== TODO: IMPLEMENT DATA LOADER =====

class DataLoader:
    """Simple loader that creates case objects from CSV data
    
    ATTRIBUTES:
    - logger: ExplainabilityLogger = For audit logging
    
    HELPFUL METHODS:
    - create_case_from_data(): Creates CaseData from input dictionaries
    
    IMPLEMENTATION PATTERN:
    1. Start timing with start_time = datetime.now()
    2. Generate case_id with str(uuid.uuid4())
    3. Create CustomerData object from customer_data dict
    4. Filter accounts where acc['customer_id'] == customer.customer_id
    5. Get account_ids set from filtered accounts
    6. Filter transactions where txn['account_id'] in account_ids
    7. Create CaseData object with all components
    8. Calculate execution_time_ms
    9. Log success/failure with self.logger.log_agent_action()
    10. Return CaseData object (or raise exception on failure)
    """
    
    def __init__(self, explainability_logger: ExplainabilityLogger):
        # TODO: Store logger for audit trail
        self.logger = explainability_logger
    
    def create_case_from_data(self, 
                            customer_data: Dict,
                            account_data: List[Dict],
                            transaction_data: List[Dict]) -> CaseData:
        """Create a unified case object from fragmented AML data

        Accepts plain ``dict`` rows (e.g. from ``DataFrame.to_dict("records")``). Integer
        ``ssn_last_4`` values and pandas NA in optional transaction strings are
        normalized before Pydantic validation.

        SUGGESTED STEPS:
        1. Record start time for performance tracking
        2. Generate unique case_id using uuid.uuid4()
        3. Create CustomerData object from customer_data dictionary
        4. Filter account_data list for accounts belonging to this customer
        5. Create AccountData objects from filtered accounts
        6. Get set of account_ids from customer's accounts
        7. Filter transaction_data for transactions in customer's accounts
        8. Create TransactionData objects from filtered transactions  
        9. Create CaseData object combining all components
        10. Add case metadata (case_id, timestamp, data_sources)
        11. Calculate execution time in milliseconds
        12. Log operation with success/failure status
        13. Return CaseData object
        
        ERROR HANDLING:
        - Wrap in try/except block
        - Log failures with error message
        - Re-raise exceptions for caller
        
        DATA_SOURCES FORMAT:
        {
            'customer_source': f"csv_extract_{datetime.now().strftime('%Y%m%d')}",
            'account_source': f"csv_extract_{datetime.now().strftime('%Y%m%d')}",
            'transaction_source': f"csv_extract_{datetime.now().strftime('%Y%m%d')}"
        }
        
        HINT: Use list comprehensions for filtering
        HINT: Use set comprehension for account_ids: {acc.account_id for acc in accounts}
        HINT: Use datetime.now(timezone.utc).isoformat() for timestamps
        HINT: Calculate execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        """
        # TODO: Implement complete case creation with error handling and logging
        start_time = datetime.now(timezone.utc)
        case_id = str(uuid.uuid4())
        try:
            # Normalize pandas/CSV-native types before models (ints, NaN in optionals).
            customer = CustomerData(**_normalize_customer_row(dict(customer_data)))
            accounts = [
                AccountData(**account)
                for account in account_data
                if account.get("customer_id") == customer.customer_id
            ]
            account_ids = {account.account_id for account in accounts}
            transactions = [
                TransactionData(**_normalize_transaction_row(dict(transaction)))
                for transaction in transaction_data
                if transaction.get("account_id") in account_ids
            ]
            data_sources = {
                "customer_source": f"csv_extract_{start_time.strftime('%Y%m%d')}",
                "account_source": f"csv_extract_{start_time.strftime('%Y%m%d')}",
                "transaction_source": f"csv_extract_{start_time.strftime('%Y%m%d')}",
            }
            case = CaseData(
                case_id=case_id,
                customer=customer,
                accounts=accounts,
                transactions=transactions,
                case_created_at=start_time.isoformat(),
                data_sources=data_sources,
            )
            execution_time_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            self.logger.log_agent_action(
                agent_type="DataLoader",
                action="create_case",
                case_id=case_id,
                input_data={
                    "customer_id": customer.customer_id,
                    "account_rows": len(account_data),
                    "transaction_rows": len(transaction_data),
                },
                output_data={
                    "case_id": case_id,
                    "accounts": len(accounts),
                    "transactions": len(transactions),
                },
                reasoning="Built unified case from customer, account, and transaction data.",
                execution_time_ms=execution_time_ms,
            )
            return case
        except Exception as exc:
            execution_time_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            self.logger.log_agent_action(
                agent_type="DataLoader",
                action="create_case",
                case_id=case_id,
                input_data={
                    "customer_id": customer_data.get("customer_id"),
                    "account_rows": len(account_data),
                    "transaction_rows": len(transaction_data),
                },
                output_data={},
                reasoning="Case creation failed; see error message.",
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(exc),
            )
            raise

# ===== HELPER FUNCTIONS (PROVIDED) =====

def load_csv_data(data_dir: str = "data/") -> tuple:
    """Load bundled AML CSVs with dtypes suited for downstream Pydantic / DataLoader.

    Enforces string types for identifiers and ``ssn_last_4`` (otherwise pandas often
    infers integers). Missing optional cells in transactions still become NA in the
    frame; ``DataLoader`` / ``TransactionData`` normalizers map those to ``None``.
    """
    try:
        customers_df = pd.read_csv(
            f"{data_dir}/customers.csv",
            dtype={"customer_id": str, "ssn_last_4": str},
        )
        accounts_df = pd.read_csv(
            f"{data_dir}/accounts.csv",
            dtype={"account_id": str, "customer_id": str},
        )
        transactions_df = pd.read_csv(
            f"{data_dir}/transactions.csv",
            dtype={"transaction_id": str, "account_id": str},
        )
        return customers_df, accounts_df, transactions_df
    except FileNotFoundError as e:
        raise FileNotFoundError(f"CSV file not found: {e}")
    except Exception as e:
        raise Exception(f"Error loading CSV data: {e}")

if __name__ == "__main__":
    print("🏗️  Foundation SAR Module")
    print("Core data schemas and utilities for SAR processing")
    print("\n📋 TODO Items:")
    print("• Implement Pydantic schemas based on CSV data")
    print("• Create ExplainabilityLogger for audit trails")
    print("• Build DataLoader for case object creation")
    print("• Add comprehensive error handling")
    print("• Write unit tests for all components")
