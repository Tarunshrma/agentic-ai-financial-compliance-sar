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
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator
import uuid
import os

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

    @field_validator("transaction_date")
    @classmethod
    def validate_transaction_date(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: float) -> float:
        if value is None:
            raise ValueError("amount is required")
        if not math.isfinite(value):
            raise ValueError("amount must be a finite number")
        if abs(value) > 1_000_000:
            raise ValueError("amount exceeds allowed maximum range")
        if value == 0:
            raise ValueError("amount must be non-zero")
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

class RiskAnalystOutput(BaseModel):
    """Risk Analyst agent structured output
    
    REQUIRED FIELDS (for Chain-of-Thought agent output):
    - classification: Literal['Structuring', 'Sanctions', 'Fraud', 'Money_Laundering', 'Other']
    - confidence_score: float = Confidence between 0.0 and 1.0 (use ge=0.0, le=1.0)
    - reasoning: str = 5-step analysis reasoning (max 500 chars)
    - key_indicators: List[str] = List of suspicious indicators found
    - risk_level: Literal['Low', 'Medium', 'High', 'Critical'] = Risk assessment
    
    HINT: Use Literal types to restrict classification and risk_level values
    HINT: Use Field(..., ge=0.0, le=1.0) for confidence_score validation
    HINT: Use Field(..., max_length=500) for reasoning length limit
    """
    classification: Literal[
        "Structuring", "Sanctions", "Fraud", "Money_Laundering", "Other"
    ] = Field(..., description="Suspicious activity classification")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )
    reasoning: str = Field(..., max_length=500, description="5-step reasoning")
    key_indicators: List[str] = Field(..., description="Key suspicious indicators")
    risk_level: Literal["Low", "Medium", "High", "Critical"] = Field(
        ..., description="Overall risk level"
    )

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning_steps(cls, value: str) -> str:
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        if len(lines) != 5:
            raise ValueError("reasoning must include exactly 5 steps")
        for idx, line in enumerate(lines, start=1):
            if not line.startswith(f"Step {idx}:"):
                raise ValueError("reasoning steps must be labeled Step 1-5")
        return value

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

# ===== TODO: IMPLEMENT AUDIT LOGGING =====

class ExplainabilityLogger:
    """Simple audit logging for compliance trails

    ATTRIBUTES:
    - log_file: str = Path to JSONL log file (default: "sar_audit.jsonl")
    - entries: List = In-memory storage of log entries

    METHODS:
    - log_agent_action(): Logs agent actions with structured data
    
    LOG ENTRY STRUCTURE (use this exact format):
    {
        'event_id': str(uuid.uuid4()),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'case_id': case_id,
        'agent_type': agent_type,  # "DataLoader", "RiskAnalyst", "ComplianceOfficer"
        'action': action,          # "create_case", "analyze_case", "generate_narrative"
        'input_data': input_data,
        'output_data': output_data,
        'input_summary': str(input_data),
        'output_summary': str(output_data),
        'reasoning': reasoning,
        'execution_time_ms': execution_time_ms,
        'success': success,        # True/False
        'error_message': error_message  # None if success=True
    }
    
    HINT: Write each entry as JSON + newline to create JSONL format
    HINT: Use 'a' mode to append to log file
    HINT: Store entries in self.entries list AND write to file
    """
    
    def __init__(self, log_file: str = "sar_audit.jsonl"):
        # TODO: Initialize with log_file path and empty entries list
        if log_file == "sar_audit.jsonl":
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
            log_file = os.path.join(
                "outputs", "audit_logs", f"sar_audit_{timestamp}.jsonl"
            )
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        self.log_file = log_file
        self.entries: List[Dict[str, Any]] = []
    
    def log_agent_action(self, agent_type: str, action: str, case_id: str, 
                        input_data: Dict, output_data: Dict, reasoning: str, 
                        execution_time_ms: float, success: bool = True, 
                        error_message: Optional[str] = None):
        """Log an agent action with essential context
        
        IMPLEMENTATION STEPS:
        1. Create entry dictionary with all fields (see structure above)
        2. Add entry to self.entries list
        3. Write entry to log file as JSON line
        
        HINT: Use json.dumps(entry) + '\n' for JSONL format
        HINT: Use datetime.now(timezone.utc).isoformat() for timestamp
        HINT: Convert input_data and output_data to strings with str()
        """
        # TODO: Implement logging with structured entry creation and file writing
        entry = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "case_id": case_id,
            "agent_type": agent_type,
            "action": action,
            "input_data": input_data,
            "output_data": output_data,
            "input_summary": str(input_data),
            "output_summary": str(output_data),
            "reasoning": reasoning,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "error_message": error_message,
        }
        self.entries.append(entry)
        with open(self.log_file, "a", encoding="utf-8") as log_handle:
            log_handle.write(json.dumps(entry) + "\n")

# ===== TODO: IMPLEMENT DATA LOADER =====

def _normalize_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value


def _normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {key: _normalize_value(value) for key, value in record.items()}
    ssn_value = normalized.get("ssn_last_4")
    if ssn_value is not None:
        if isinstance(ssn_value, float) and ssn_value.is_integer():
            ssn_value = int(ssn_value)
        normalized["ssn_last_4"] = str(ssn_value).zfill(4)
    return normalized


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
            normalized_customer = _normalize_record(customer_data)
            normalized_accounts = [
                _normalize_record(account) for account in account_data
            ]
            normalized_transactions = [
                _normalize_record(transaction) for transaction in transaction_data
            ]
            customer = CustomerData(**normalized_customer)
            accounts = [
                AccountData(**account)
                for account in normalized_accounts
                if account.get("customer_id") == customer.customer_id
            ]
            account_ids = {account.account_id for account in accounts}
            transactions = [
                TransactionData(**transaction)
                for transaction in normalized_transactions
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

    def create_case_from_csv(self, customer_id: str, data_dir: str = "data/") -> CaseData:
        """Create a case directly from CSV sources for a given customer."""
        customers_df, accounts_df, transactions_df = load_csv_data(data_dir)

        customer_rows = customers_df.loc[
            customers_df["customer_id"] == customer_id
        ].to_dict(orient="records")
        if not customer_rows:
            raise ValueError(f"Customer {customer_id} not found in CSV data")

        account_rows = accounts_df.loc[
            accounts_df["customer_id"] == customer_id
        ].to_dict(orient="records")
        transaction_rows = transactions_df.to_dict(orient="records")

        return self.create_case_from_data(
            customer_rows[0], account_rows, transaction_rows
        )

# ===== HELPER FUNCTIONS (PROVIDED) =====

def load_csv_data(data_dir: str = "data/") -> tuple:
    """Helper function to load all CSV files
    
    Returns:
        tuple: (customers_df, accounts_df, transactions_df)
    """
    try:
        customers_df = pd.read_csv(
            f"{data_dir}/customers.csv", dtype={"ssn_last_4": str}
        )
        accounts_df = pd.read_csv(f"{data_dir}/accounts.csv")
        transactions_df = pd.read_csv(f"{data_dir}/transactions.csv")
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
