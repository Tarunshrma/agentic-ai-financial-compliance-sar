# Foundation SAR Tests - Top 10 Essential Tests

"""
Streamlined test suite for foundation_sar.py module focusing on core functionality
"""

import pytest
import os
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

# Import foundation components - these will work once students implement them
try:
    from src.foundation_sar import (
        CustomerData,
        AccountData, 
        TransactionData,
        CaseData,
        ExplainabilityLogger,
        DataLoader,
        load_csv_data,
        audit_session_timestamp_utc,
        audit_jsonl_path,
        filed_sar_json_path,
    )
    
    # Test if classes are actually implemented (not just empty pass statements)
    try:
        # Check if CustomerData has proper fields defined, not just an empty pass
        # If the class is just "pass", it won't have any model fields
        if hasattr(CustomerData, 'model_fields') and CustomerData.model_fields:
            # Try to create a simple instance to see if it's properly implemented
            test_customer = CustomerData(
                customer_id="TEST", 
                name="Test", 
                date_of_birth="1990-01-01",
                ssn_last_4="1234",
                address="123 Test St",
                customer_since="2020-01-01",
                risk_rating="Low", 
                annual_income=50000
            )
            # If we get here, the implementation exists and works
            FOUNDATION_IMPLEMENTED = True
        else:
            # No model fields defined - just empty pass statements
            FOUNDATION_IMPLEMENTED = False
    except Exception as e:
        # Any error means implementation is incomplete
        FOUNDATION_IMPLEMENTED = False
        
except ImportError:
    # Graceful fallback when students haven't implemented yet
    FOUNDATION_IMPLEMENTED = False

if not FOUNDATION_IMPLEMENTED:
    print("⚠️  Foundation components not yet implemented - tests will be skipped")
    print("💡 Implement the classes in src/foundation_sar.py to run these tests")

class TestCustomerData:
    """Test CustomerData Pydantic schema"""
    
    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_valid_customer_data(self):
        """Test CustomerData with complete valid inputs"""
        customer_data = {
            "customer_id": "CUST_0001",
            "name": "Allison Hill",
            "date_of_birth": "1958-08-25",
            "ssn_last_4": "2679",
            "address": "600 Jeffery Parkways, New Jamesside, MT 29394",
            "phone": "394.802.6542x351",
            "customer_since": "2016-06-14",
            "risk_rating": "Low",
            "occupation": "Local government officer",
            "annual_income": 48815
        }
        
        customer = CustomerData(**customer_data)
        assert customer.customer_id == "CUST_0001"
        assert customer.name == "Allison Hill"
        assert customer.risk_rating == "Low"
        assert customer.annual_income == 48815

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_customer_pandas_native_types(self):
        """int ssn_last_4 and NaN optional fields from pandas to_dict must validate."""
        customer_data = {
            "customer_id": "CUST_0001",
            "name": "Allison Hill",
            "date_of_birth": "1958-08-25",
            "ssn_last_4": 2679,
            "address": "600 Jeffery Parkways, New Jamesside, MT 29394",
            "phone": float("nan"),
            "customer_since": "2016-06-14",
            "risk_rating": "Low",
            "occupation": float("nan"),
            "annual_income": float("nan"),
        }
        customer = CustomerData(**customer_data)
        assert customer.ssn_last_4 == "2679"
        assert customer.phone is None
        assert customer.occupation is None
        assert customer.annual_income is None

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_customer_ssn_last_4_zero_pad_from_int(self):
        """Leading-zero SSN fragments stored as smaller ints become 4-digit strings."""
        customer_data = {
            "customer_id": "CUST_X",
            "name": "Test",
            "date_of_birth": "1980-01-01",
            "ssn_last_4": 79,
            "address": "123 St",
            "customer_since": "2020-01-01",
            "risk_rating": "Low",
        }
        customer = CustomerData(**customer_data)
        assert customer.ssn_last_4 == "0079"

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_customer_risk_rating_validation(self):
        """Test CustomerData risk rating validation"""
        # Test valid risk ratings
        for rating in ["Low", "Medium", "High"]:
            customer = CustomerData(
                customer_id=f"CUST_{rating}",
                name="Test Customer",
                date_of_birth="1980-01-01",
                ssn_last_4="1234",
                address="123 Test St",
                customer_since="2020-01-01",
                risk_rating=rating
            )
            assert customer.risk_rating == rating

class TestAccountData:
    """Test AccountData Pydantic schema"""
    
    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_valid_account_data(self):
        """Test AccountData with valid inputs"""
        account_data = {
            "account_id": "CUST_0001_ACC_1",
            "customer_id": "CUST_0001",
            "account_type": "Checking",
            "opening_date": "2016-06-14",
            "current_balance": 51690.75,
            "average_monthly_balance": 45000.00,
            "status": "Active"
        }
        
        account = AccountData(**account_data)
        assert account.account_id == "CUST_0001_ACC_1"
        assert account.account_type == "Checking"
        assert account.current_balance == 51690.75
        assert account.status == "Active"

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_account_balance_validation(self):
        """Test AccountData balance validation"""
        # Test zero balance
        account = AccountData(
            account_id="ACC_TEST",
            customer_id="CUST_TEST",
            account_type="Checking",
            opening_date="2020-01-01",
            current_balance=0.0,
            average_monthly_balance=0.0,
            status="Active"
        )
        assert account.current_balance == 0.0

class TestTransactionData:
    """Test TransactionData Pydantic schema"""
    
    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_valid_transaction_data(self):
        """Test TransactionData with valid inputs"""
        transaction_data = {
            "transaction_id": "TXN_B24455F3",
            "account_id": "CUST_0001_ACC_1",
            "transaction_date": "2025-01-08",
            "transaction_type": "Online_Transfer",
            "amount": 9900.0,
            "description": "ONLINE TRANSFER TO SAVINGS",
            "counterparty": "WELLS FARGO BANK",
            "location": "ONLINE",
            "method": "ACH"
        }
        
        transaction = TransactionData(**transaction_data)
        assert transaction.transaction_id == "TXN_B24455F3"
        assert transaction.amount == 9900.0
        assert transaction.transaction_type == "Online_Transfer"

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_transaction_optional_fields_nan_to_none(self):
        """Empty optional text columns parsed as float NaN must become None."""
        transaction_data = {
            "transaction_id": "TXN_B24455F3",
            "account_id": "CUST_0002_ACC_1",
            "transaction_date": "2025-02-18",
            "transaction_type": "Online_Transfer",
            "amount": 1615.06,
            "description": "Credit card payment",
            "counterparty": float("nan"),
            "location": "Branch_Westside_Plaza",
            "method": "ATM",
        }
        transaction = TransactionData(**transaction_data)
        assert transaction.counterparty is None
        assert transaction.location == "Branch_Westside_Plaza"

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_transaction_amount_validation(self):
        """Test TransactionData amount validation"""
        # Test positive amount
        transaction = TransactionData(
            transaction_id="TXN_TEST",
            account_id="ACC_TEST",
            transaction_date="2025-01-01",
            transaction_type="Deposit",
            amount=100.50,
            description="Test deposit",
            method="ACH"
        )
        assert transaction.amount == 100.50

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_transaction_amount_negative_debit_allowed(self):
        """Debits modeled as negative amounts stay within magnitude bounds."""
        transaction = TransactionData(
            transaction_id="TXN_DEBIT",
            account_id="ACC_TEST",
            transaction_date="2025-01-01",
            transaction_type="ACH_Debit",
            amount=-2500.0,
            description="Debit",
            method="ACH",
        )
        assert transaction.amount == -2500.0

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_transaction_amount_rejects_non_finite_and_out_of_range(self):
        """Reject NaN, zero, and unrealistically large magnitudes."""
        base = dict(
            transaction_id="TXN_X",
            account_id="ACC_TEST",
            transaction_date="2025-01-01",
            transaction_type="Wire_Transfer",
            description="Test",
            method="Wire",
        )
        with pytest.raises(Exception):
            TransactionData(**base, amount=float("nan"))
        with pytest.raises(Exception):
            TransactionData(**base, amount=0.0)
        with pytest.raises(Exception):
            TransactionData(**base, amount=1e15)

class TestCaseData:
    """Test CaseData unified schema"""
    
    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_valid_case_creation(self):
        """Test creating a valid case with all components"""
        # Create sample customer
        customer = CustomerData(
            customer_id="CUST_0001",
            name="Test Customer",
            date_of_birth="1980-01-01",
            ssn_last_4="1234",
            address="123 Test St",
            customer_since="2020-01-01",
            risk_rating="Medium",
            annual_income=75000
        )
        
        # Create sample account
        account = AccountData(
            account_id="CUST_0001_ACC_1",
            customer_id="CUST_0001",
            account_type="Checking",
            opening_date="2020-01-01",
            current_balance=10000.0,
            average_monthly_balance=8000.0,
            status="Active"
        )
        
        # Create sample transaction
        transaction = TransactionData(
            transaction_id="TXN_001",
            account_id="CUST_0001_ACC_1",
            transaction_date="2025-01-01",
            transaction_type="Cash_Deposit",
            amount=9900.0,
            description="Cash deposit just under threshold",
            method="Cash"
        )
        
        # Create unified case
        case = CaseData(
            case_id="CASE_001",
            customer=customer,
            accounts=[account],
            transactions=[transaction],
            case_created_at=datetime.now().isoformat(),
            data_sources={
                "customer_source": "test_data",
                "account_source": "test_data", 
                "transaction_source": "test_data"
            }
        )
        
        assert case.case_id == "CASE_001"
        assert case.customer.customer_id == "CUST_0001"
        assert len(case.accounts) == 1
        assert len(case.transactions) == 1

class TestDataLoader:
    """Test DataLoader functionality"""
    
    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_csv_data_loading(self):
        """Test DataLoader can create cases from data"""
        logger = ExplainabilityLogger("test_audit.jsonl")
        loader = DataLoader(logger)
        
        # Sample data with all required fields
        customer_data = {
            "customer_id": "CUST_0001",
            "name": "Test Customer",
            "date_of_birth": "1980-01-01",
            "ssn_last_4": "1234",
            "address": "123 Test St",
            "customer_since": "2020-01-01",
            "risk_rating": "Medium",
            "annual_income": 75000
        }
        
        account_data = [{
            "account_id": "CUST_0001_ACC_1",
            "customer_id": "CUST_0001",
            "account_type": "Checking",
            "opening_date": "2020-01-01",
            "current_balance": 10000.0,
            "average_monthly_balance": 8000.0,
            "status": "Active"
        }]
        
        transaction_data = [{
            "transaction_id": "TXN_001",
            "account_id": "CUST_0001_ACC_1",
            "transaction_date": "2025-01-01",
            "transaction_type": "Cash_Deposit",
            "amount": 9900.0,
            "description": "Test transaction",
            "method": "Cash"
        }]
        
        case = loader.create_case_from_data(customer_data, account_data, transaction_data)
        assert case is not None
        assert case.customer.customer_id == "CUST_0001"
        assert len(case.accounts) == 1
        assert len(case.transactions) == 1
        
        # Cleanup
        if os.path.exists("test_audit.jsonl"):
            os.remove("test_audit.jsonl")

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_dataloader_plain_read_csv_integration(self):
        """Untyped pandas read_csv + to_dict(records): int SSN and NaN optionals reach CaseData."""
        import pandas as pd

        data_dir = Path(__file__).resolve().parent.parent / "data"
        customers_df = pd.read_csv(data_dir / "customers.csv")
        accounts_df = pd.read_csv(data_dir / "accounts.csv")
        transactions_df = pd.read_csv(data_dir / "transactions.csv")
        customers = customers_df.to_dict("records")
        accounts = accounts_df.to_dict("records")
        transactions = transactions_df.to_dict("records")

        cust = next(c for c in customers if c["customer_id"] == "CUST_0002")
        assert isinstance(cust["ssn_last_4"], int)

        logger = ExplainabilityLogger(log_file=os.devnull)
        loader = DataLoader(logger)
        case = loader.create_case_from_data(cust, accounts, transactions)

        assert case.customer.ssn_last_4 == str(cust["ssn_last_4"])
        assert len(case.transactions) > 0
        assert any(txn.counterparty is None for txn in case.transactions)
        assert pd.isna(transactions_df.iloc[0]["counterparty"]), (
            "expected sample row with blank counterparty (CSV empty cell)"
        )


class TestNotebookOutputNaming:
    """outputs/audit_logs JSONL + outputs/filed_sars JSON naming conventions."""

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_audit_and_filed_sar_paths(self):
        tmp = tempfile.mkdtemp()
        try:
            ts = "20990102_030405"
            ap = audit_jsonl_path(tmp, stem="workflow_integration", session_timestamp_utc=ts)
            assert os.path.basename(ap) == f"workflow_integration_run_{ts}.jsonl"
            assert os.path.isdir(os.path.join(tmp, "audit_logs"))
            sp = filed_sar_json_path(
                tmp,
                session_timestamp_utc=ts,
                case_id="case_uuid_001",
                sar_id="SAR_asset_uuid",
            )
            assert os.path.isdir(os.path.join(tmp, "filed_sars"))
            assert ts in os.path.basename(sp)
            assert "__case_" in os.path.basename(sp)
        finally:
            shutil.rmtree(tmp)

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_audit_session_timestamp_shape(self):
        ts = audit_session_timestamp_utc()
        assert "_" in ts
        assert ts[8] == "_"


class TestExplainabilityLogger:
    """Test ExplainabilityLogger audit functionality"""
    
    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_log_creation(self):
        """Test ExplainabilityLogger can create log entries"""
        logger = ExplainabilityLogger("test_log.jsonl")
        
        logger.log_agent_action(
            agent_type="TestAgent",
            action="test_action",
            case_id="CASE_001",
            input_data={"test": "input"},
            output_data={"test": "output"},
            reasoning="Test reasoning",
            execution_time_ms=100.0,
            success=True
        )
        
        assert len(logger.entries) == 1
        assert logger.entries[0]["agent_type"] == "TestAgent"
        assert logger.entries[0]["case_id"] == "CASE_001"
        assert "event_id" in logger.entries[0]
        assert len(logger.entries[0]["event_id"]) == 36
        assert logger.entries[0]["inputs"] == {"test": "input"}
        assert logger.entries[0]["outputs"] == {"test": "output"}
        assert json.loads(json.dumps(logger.entries[0])) == logger.entries[0]
        
        # Cleanup
        if os.path.exists("test_log.jsonl"):
            os.remove("test_log.jsonl")

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_log_entry_uses_json_objects_not_string_blobs(self):
        """Reviewer-facing JSONL rows must expose nested payloads as JSON, not Python repr."""
        log_file = "test_struct_audit.jsonl"
        logger = ExplainabilityLogger(log_file)
        logger.log_agent_action(
            agent_type="HumanReviewer",
            action="human_gate_decision",
            case_id="CASE_GATE",
            input_data={"risk_analysis": {"classification": "Other"}},
            output_data={"decision": "REJECT"},
            reasoning="Structured human gate audit row.",
            execution_time_ms=0.0,
            success=True,
        )
        with open(log_file, encoding="utf-8") as fh:
            parsed = json.loads(fh.readline())
        assert parsed["inputs"]["risk_analysis"]["classification"] == "Other"
        assert parsed["outputs"]["decision"] == "REJECT"
        assert isinstance(parsed["inputs"], dict)
        if os.path.exists(log_file):
            os.remove(log_file)

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_each_log_entry_has_unique_event_id(self):
        """event_id distinguishes audit lines that share the same case_id."""
        log_file = "test_event_id.jsonl"
        logger = ExplainabilityLogger(log_file)
        logger.log_agent_action(
            agent_type="TestAgent",
            action="a",
            case_id="CASE_SHARED",
            input_data={},
            output_data={},
            reasoning="first",
            execution_time_ms=1.0,
            success=True,
        )
        logger.log_agent_action(
            agent_type="TestAgent",
            action="b",
            case_id="CASE_SHARED",
            input_data={},
            output_data={},
            reasoning="second",
            execution_time_ms=2.0,
            success=True,
        )
        assert logger.entries[0]["event_id"] != logger.entries[1]["event_id"]

        with open(log_file) as fh:
            lines = fh.readlines()
        assert json.loads(lines[0])["event_id"] != json.loads(lines[1])["event_id"]
        if os.path.exists(log_file):
            os.remove(log_file)

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_log_file_writing(self):
        """Test ExplainabilityLogger writes to file"""
        log_file = "test_file_log.jsonl"
        logger = ExplainabilityLogger(log_file)
        
        # Log multiple entries
        for i in range(3):
            logger.log_agent_action(
                agent_type="TestAgent",
                action=f"test_action_{i}",
                case_id=f"CASE_{i:03d}",
                input_data={"iteration": i},
                output_data={"result": f"output_{i}"},
                reasoning=f"Test reasoning {i}",
                execution_time_ms=50.0 + i,
                success=True
            )
        
        # Check file exists and has content
        assert os.path.exists(log_file)
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 3
        ids = [json.loads(line)["event_id"] for line in lines]
        assert len(set(ids)) == 3
        
        # Cleanup
        if os.path.exists(log_file):
            os.remove(log_file)


def _format_csv_schema_summary(result: dict) -> str:
    lines = ["Sample CSV row schema validation summary:"]
    for sec in result["sections"]:
        status = "PASS" if sec["pass"] else "FAIL"
        lines.append(
            f"  {status}  {sec['file']} ({sec['model']}): "
            f"{sec['passed_rows']}/{sec['total_rows']} rows ok"
        )
        if sec.get("sample_errors"):
            lines.append(f"    first error: {sec['sample_errors'][0]}")
    lines.append(f"  OVERALL: {'PASS' if result['all_csv_rows_pass'] else 'FAIL'}")
    return "\n".join(lines)


def _validate_every_csv_row_against_models(data_dir: str) -> dict:
    """Full validation across the three sample CSVs; summary for assertions only."""
    customers_df, accounts_df, transactions_df = load_csv_data(data_dir)

    def _validate_file(file_label: str, model_cls, df):
        failures = []
        records = df.to_dict("records")
        for idx, row in enumerate(records):
            try:
                model_cls(**row)
            except Exception as exc:
                failures.append({"row_index": idx, "error": str(exc)})
        total = len(records)
        failed = len(failures)
        return {
            "file": file_label,
            "model": model_cls.__name__,
            "total_rows": total,
            "passed_rows": total - failed,
            "failed_rows": failed,
            "pass": failed == 0,
            "sample_errors": failures[:5],
        }

    sections = [
        _validate_file("customers.csv", CustomerData, customers_df),
        _validate_file("accounts.csv", AccountData, accounts_df),
        _validate_file("transactions.csv", TransactionData, transactions_df),
    ]
    return {
        "all_csv_rows_pass": all(s["pass"] for s in sections),
        "sections": sections,
    }


def _validate_dataloader_cases_where_transactions_exist(data_dir: str) -> dict:
    """Optional end-to-end check: DataLoader + CaseData for customers with ≥1 txn."""
    customers_df, accounts_df, transactions_df = load_csv_data(data_dir)
    customers = customers_df.to_dict("records")
    accounts = accounts_df.to_dict("records")
    transactions = transactions_df.to_dict("records")
    logger = ExplainabilityLogger(log_file=os.devnull)
    loader = DataLoader(logger)

    skipped_no_txn = 0
    case_failures = []
    cases_built = 0

    for cust in customers:
        cid = cust["customer_id"]
        cust_accounts = [a for a in accounts if a.get("customer_id") == cid]
        account_ids = {a.get("account_id") for a in cust_accounts}
        cust_txns = [t for t in transactions if t.get("account_id") in account_ids]
        if not cust_txns:
            skipped_no_txn += 1
            continue
        try:
            loader.create_case_from_data(cust, accounts, transactions)
            cases_built += 1
        except Exception as exc:
            case_failures.append({"customer_id": cid, "error": str(exc)})

    total_with_txn = cases_built + len(case_failures)
    return {
        "customers_total": len(customers),
        "customers_skipped_no_transactions": skipped_no_txn,
        "customers_with_transactions": total_with_txn,
        "cases_built_ok": cases_built,
        "cases_failed": len(case_failures),
        "all_cases_pass": len(case_failures) == 0 and total_with_txn > 0,
        "sample_case_errors": case_failures[:5],
    }


class TestSampleCsvEndToEndValidation:
    """Full validation of bundled `data/*.csv` rows (requirement); loader check optional."""

    DATA_DIR = str(Path(__file__).resolve().parent.parent / "data")

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_all_sample_csv_rows_validate_against_schemas(self):
        """Every row in customers, accounts, and transactions CSVs must validate."""
        result = _validate_every_csv_row_against_models(self.DATA_DIR)
        assert result["all_csv_rows_pass"], _format_csv_schema_summary(result)

    @pytest.mark.skipif(not FOUNDATION_IMPLEMENTED, reason="Foundation not implemented yet")
    def test_dataloader_builds_case_for_each_customer_with_transactions(self):
        """CaseData requires non-empty transactions; cover all customers who have any."""
        result = _validate_dataloader_cases_where_transactions_exist(self.DATA_DIR)
        msg_lines = [
            "DataLoader case build summary (customers with ≥1 transaction only):",
            f"  customers_total={result['customers_total']}",
            f"  customers_skipped_no_transactions={result['customers_skipped_no_transactions']}",
            f"  customers_with_transactions={result['customers_with_transactions']}",
            f"  cases_built_ok={result['cases_built_ok']}",
            f"  cases_failed={result['cases_failed']}",
        ]
        if result.get("sample_case_errors"):
            msg_lines.append(f"  sample_case_errors={result['sample_case_errors']}")
        msg = "\n".join(msg_lines)
        assert result["all_cases_pass"], msg