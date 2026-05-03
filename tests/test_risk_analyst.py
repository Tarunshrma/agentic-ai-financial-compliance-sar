# Risk Analyst Agent Tests - Top 10 Essential Tests

"""
Streamlined test suite for risk_analyst_agent.py module focusing on core functionality
"""

import pytest
import json
import os
from typing import List

from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Foundation types used by parametrized scenario builders (must load even before agent probing)
try:
    from src.foundation_sar import (
        RiskAnalystOutput,
        ExplainabilityLogger,
        CaseData,
        CustomerData,
        AccountData,
        TransactionData,
        RISK_LEVEL_CONFIDENCE_BANDS,
        risk_analyst_output_parse_fallback,
    )
except ImportError:  # pragma: no cover
    RiskAnalystOutput = None  # type: ignore
    ExplainabilityLogger = None  # type: ignore
    CaseData = None  # type: ignore
    CustomerData = None  # type: ignore
    AccountData = None  # type: ignore
    TransactionData = None  # type: ignore
    RISK_LEVEL_CONFIDENCE_BANDS = {}
    risk_analyst_output_parse_fallback = None  # type: ignore

try:
    from src.risk_analyst_agent import RiskAnalystAgent
    
    # Test if RiskAnalystAgent is actually implemented (not just empty pass statements)
    try:
        # Check if RiskAnalystAgent has proper methods defined, not just an empty pass
        # If the class methods are just "pass", they won't have proper implementations
        mock_client = Mock()
        mock_logger = Mock()
        test_agent = RiskAnalystAgent(mock_client, mock_logger)
        
        # Check if the agent has the required methods and attributes with proper implementation
        # Check if system_prompt has real content (not just TODO placeholder)
        has_real_prompt = (hasattr(test_agent, 'system_prompt') and 
                          test_agent.system_prompt is not None and
                          len(str(test_agent.system_prompt)) > 50 and
                          "TODO" not in test_agent.system_prompt)
        
        # Check if analyze_case method exists and is not just a pass statement
        # Try calling it to see if it's implemented
        has_real_analyze = False
        if hasattr(test_agent, 'analyze_case') and callable(getattr(test_agent, 'analyze_case', None)):
            try:
                # A properly implemented analyze_case should raise an error or return something when called
                # An empty pass statement will just return None
                result = test_agent.analyze_case(None)
                # If it returns None for None input, it's likely just a pass statement
                has_real_analyze = result is not None
            except Exception:
                # If it raises an exception, it means there's some implementation (good!)
                has_real_analyze = True
        
        # Check if helper methods exist and are implemented
        has_extract_json = (hasattr(test_agent, '_extract_json_from_response') and
                           callable(getattr(test_agent, '_extract_json_from_response', None)))
        
        # Only consider it implemented if it has real content, not just placeholder methods
        if has_real_prompt and has_real_analyze and has_extract_json:
            RISK_ANALYST_IMPLEMENTED = True
        else:
            # Missing required implementation - just placeholder methods
            RISK_ANALYST_IMPLEMENTED = False
    except Exception as e:
        # Any error means implementation is incomplete
        RISK_ANALYST_IMPLEMENTED = False
        
except ImportError:
    # Graceful fallback when students haven't implemented yet
    RISK_ANALYST_IMPLEMENTED = False

if not RISK_ANALYST_IMPLEMENTED:
    print("⚠️  Risk Analyst Agent not yet implemented - tests will be skipped")
    print("💡 Implement the RiskAnalystAgent class in src/risk_analyst_agent.py to run these tests")


def _risk_response_steps_for_classification(classification: str) -> list:
    """Five CoT strings aligned to RiskAnalystOutput  (five framework steps per case type)."""
    return [
        f"Data Review: reviewed Scenario {classification} customer profile, balances, "
        "and enumerated transactions for this case fixture only.",
        f"Pattern Recognition: mapped transaction shapes to {classification}-style indicators "
        "seen in staged test data.",
        "Regulatory Mapping: tied observed behaviors to AML/BSA filing expectations "
        "without asserting facts absent from CSV.",
        f"Risk Quantification: midpoint confidence selected within the calibrated band "
        f"paired with this scenario's risk tier.",
        f"Classification Decision: commit to `{classification}` as the lone label versus alternatives.",
    ]


def _customer_risk_for_scenario_level(risk_level: str) -> str:
    if risk_level in ("Critical", "High"):
        return "High"
    if risk_level == "Medium":
        return "Medium"
    return "Low"


def _scenario_case_for_classification(classification: str, risk_level: str) -> CaseData:
    """
    Distinct CaseData fixtures per SAR type so prompts and parsing tests exercise heterogeneous
    transaction shapes (structuring vs layering vs benign mix, etc.).
    """
    cr = _customer_risk_for_scenario_level(risk_level)
    customer = CustomerData(
        customer_id="CUST_SCENARIO",
        name=f"Scenario {classification}",
        date_of_birth="1985-06-01",
        ssn_last_4="5678",
        address="Scenario Row, Testburg",
        customer_since="2019-01-01",
        risk_rating=cr,
    )
    account = AccountData(
        account_id="ACC_SCENARIO",
        customer_id="CUST_SCENARIO",
        account_type="Checking",
        opening_date="2019-02-01",
        current_balance=125_000.0,
        average_monthly_balance=45_000.0,
        status="Active",
    )

    txs: List[TransactionData]
    if classification == "Structuring":
        txs = [
            TransactionData(
                transaction_id="TX_S1",
                account_id="ACC_SCENARIO",
                transaction_date="2025-02-03",
                transaction_type="Cash_Deposit",
                amount=2_955.00,
                description="Cash under usual CTR scrutiny band",
                method="Cash",
                location="Branch_Downtown",
            ),
            TransactionData(
                transaction_id="TX_S2",
                account_id="ACC_SCENARIO",
                transaction_date="2025-02-04",
                transaction_type="Cash_Deposit",
                amount=2_980.00,
                description="Similar denomination sequencing",
                method="Cash",
                location="Branch_Downtown",
            ),
            TransactionData(
                transaction_id="TX_S3",
                account_id="ACC_SCENARIO",
                transaction_date="2025-02-05",
                transaction_type="Cash_Deposit",
                amount=2_990.00,
                description="Repeated sub-threshold structuring pattern",
                method="Cash",
                location="ATM_Network",
            ),
        ]
    elif classification == "Sanctions":
        txs = [
            TransactionData(
                transaction_id="TX_N1",
                account_id="ACC_SCENARIO",
                transaction_date="2025-03-10",
                transaction_type="Wire_Transfer",
                amount=185_000.0,
                description="Outbound wire high-risk correspondent jurisdiction",
                method="Swift",
                location="Intl_Hub_A",
            ),
            TransactionData(
                transaction_id="TX_N2",
                account_id="ACC_SCENARIO",
                transaction_date="2025-03-12",
                transaction_type="Wire_Transfer",
                amount=142_300.0,
                description="Returned wire noted OFAC-style counterparty cue in memo",
                method="Swift",
            ),
        ]
    elif classification == "Fraud":
        txs = [
            TransactionData(
                transaction_id="TX_F1",
                account_id="ACC_SCENARIO",
                transaction_date="2025-04-02",
                transaction_type="ACH_Debit",
                amount=22_450.0,
                description="Sudden ACH pull inconsistent with payroll profile",
                method="ACH",
            ),
            TransactionData(
                transaction_id="TX_F2",
                account_id="ACC_SCENARIO",
                transaction_date="2025-04-02",
                transaction_type="Wire_Transfer",
                amount=19_995.0,
                description="ATO-style outbound wire minutes after ACH debit",
                method="Online",
            ),
        ]
    elif classification == "Money_Laundering":
        txs = [
            TransactionData(
                transaction_id="TX_M1",
                account_id="ACC_SCENARIO",
                transaction_date="2025-01-16",
                transaction_type="Wire_Transfer",
                amount=97_800.0,
                description="Inbound from shell-style intermediary",
                method="Wire",
            ),
            TransactionData(
                transaction_id="TX_M2",
                account_id="ACC_SCENARIO",
                transaction_date="2025-01-18",
                transaction_type="ACH_Credit",
                amount=93_750.0,
                description="Sweep to secondary DDA layering leg",
                method="ACH",
            ),
            TransactionData(
                transaction_id="TX_M3",
                account_id="ACC_SCENARIO",
                transaction_date="2025-01-20",
                transaction_type="Wire_Transfer",
                amount=91_250.0,
                description="Outbound to unrelated entity same week",
                method="Swift",
            ),
        ]
    else:  # Other
        txs = [
            TransactionData(
                transaction_id="TX_O1",
                account_id="ACC_SCENARIO",
                transaction_date="2025-06-02",
                transaction_type="Debit_Purchase",
                amount=42.87,
                description="Coffee purchase",
                method="Card",
            ),
            TransactionData(
                transaction_id="TX_O2",
                account_id="ACC_SCENARIO",
                transaction_date="2025-06-03",
                transaction_type="ACH_Credit",
                amount=1_850.50,
                description="Employer payroll ACH",
                method="ACH",
            ),
        ]

    return CaseData(
        case_id=f"CASE_SCENARIO_{classification}_{risk_level}",
        customer=customer,
        accounts=[account],
        transactions=txs,
        case_created_at=datetime.now().isoformat(),
        data_sources={
            "test": "scenario_fixture",
            "classification_fixture": classification,
        },
    )


class TestRiskAnalystAgent:
    """Test RiskAnalystAgent core functionality"""
    
    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_agent_initialization(self):
        """Test RiskAnalystAgent initializes properly"""
        mock_client = Mock()
        logger = ExplainabilityLogger("test_risk.jsonl")
        
        agent = RiskAnalystAgent(mock_client, logger, model="gpt-4")
        
        assert agent.client == mock_client
        assert agent.logger == logger
        assert agent.model == "gpt-4"
        assert agent.system_prompt is not None
        assert len(agent.system_prompt) > 100  # Should have substantial prompt
        
        # Cleanup
        if os.path.exists("test_risk.jsonl"):
            os.remove("test_risk.jsonl")
    
    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_analyze_case_success(self):
        """Test successful case analysis with valid response"""
        # Setup mock OpenAI client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
{
    "classification": "Structuring",
    "confidence_score": 0.85,
    "reasoning_steps": [
        "Reviewed checking account showing repeated deposits under reporting threshold.",
        "Observed clustered cash deposits and round amounts consistent with CTR avoidance.",
        "Mapped indicators to structuring typology referenced under BSA obligations.",
        "High confidence due to sequencing and denomination patterns in source data.",
        "Classification Structuring fits best versus laundering-only or fraud hypotheses."
    ],
    "key_indicators": ["threshold avoidance", "repeated amounts", "cash deposits"],
    "risk_level": "High"
}
```'''
        mock_client.chat.completions.create.return_value = mock_response
        
        # Setup logger
        logger = ExplainabilityLogger("test_analyze.jsonl")
        agent = RiskAnalystAgent(mock_client, logger)
        
        # Create test case data
        customer = CustomerData(
            customer_id="CUST_TEST",
            name="Test Customer", 
            date_of_birth="1980-01-01",
            ssn_last_4="1234",
            address="123 Test St",
            customer_since="2020-01-01",
            risk_rating="Medium"
        )
        
        account = AccountData(
            account_id="ACC_TEST",
            customer_id="CUST_TEST",
            account_type="Checking",
            opening_date="2020-01-01",
            current_balance=15000.0,
            average_monthly_balance=12000.0,
            status="Active"
        )
        
        transaction = TransactionData(
            transaction_id="TXN_TEST",
            account_id="ACC_TEST",
            transaction_date="2025-01-01",
            transaction_type="Cash_Deposit",
            amount=9900.0,
            description="Cash deposit",
            method="Cash"
        )
        
        case = CaseData(
            case_id="CASE_TEST",
            customer=customer,
            accounts=[account],
            transactions=[transaction],
            case_created_at=datetime.now().isoformat(),
            data_sources={"test": "data"}
        )
        
        # Run analysis
        result = agent.analyze_case(case)
        
        # Verify result
        assert isinstance(result, RiskAnalystOutput)
        assert result.classification == "Structuring"
        assert result.confidence_score == 0.85
        assert result.risk_level == "High"
        assert len(result.key_indicators) == 3
        assert len(result.reasoning_steps) == 5
        assert all(len(s.strip()) > 0 for s in result.reasoning_steps)

        # Verify API was called
        mock_client.chat.completions.create.assert_called_once()
        
        # Verify logging
        assert len(logger.entries) == 1
        assert logger.entries[0]["success"] == True
        assert logger.entries[0]["agent_type"] == "RiskAnalyst"
        
        # Cleanup
        if os.path.exists("test_analyze.jsonl"):
            os.remove("test_analyze.jsonl")

    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    @pytest.mark.parametrize(
        "classification,risk_level,key_tag",
        [
            ("Structuring", "High", "cash_threshold_pattern"),
            ("Sanctions", "Critical", "ofac_style_counterparty"),
            ("Fraud", "High", "account_takeover_signals"),
            ("Money_Laundering", "Critical", "layering_velocity"),
            ("Other", "Low", "inconclusive_benign_mix"),
        ],
    )
    def test_analyze_case_each_sar_classification_end_to_end(
        self, classification, risk_level, key_tag
    ):
        """Full agent path: mocked API returns each Literal label; RiskAnalystOutput validates it."""
        payload = {
            "classification": classification,
            "confidence_score": round(
                (
                    RISK_LEVEL_CONFIDENCE_BANDS[risk_level][0]
                    + RISK_LEVEL_CONFIDENCE_BANDS[risk_level][1]
                )
                / 2,
                3,
            ),
            "reasoning_steps": _risk_response_steps_for_classification(classification),
            "key_indicators": [key_tag, "scenario_test_marker"],
            "risk_level": risk_level,
        }
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(payload)
        mock_client.chat.completions.create.return_value = mock_response

        logger = ExplainabilityLogger(log_file=os.devnull)
        agent = RiskAnalystAgent(mock_client, logger)

        case = _scenario_case_for_classification(classification, risk_level)

        result = agent.analyze_case(case)

        assert isinstance(result, RiskAnalystOutput)
        assert result.classification == classification
        assert result.risk_level == risk_level
        lo, hi = RISK_LEVEL_CONFIDENCE_BANDS[risk_level]
        assert lo <= result.confidence_score <= hi
        assert len(result.reasoning_steps) == 5
        assert all(len(step.strip()) > 0 for step in result.reasoning_steps)
        assert result.reasoning_steps == payload["reasoning_steps"]

        msgs = mock_client.chat.completions.create.call_args.kwargs["messages"]
        user_blob = msgs[1]["content"]
        subtype_markers = {
            "Structuring": ("Cash_Deposit", "$2,955.00"),
            "Sanctions": ("Wire_Transfer", "$185,000"),
            "Fraud": ("ACH_Debit", "ATO-style"),
            "Money_Laundering": ("shell-style", "$97,800"),
            "Other": ("Coffee purchase", "$42.87"),
        }
        a, b = subtype_markers[classification]
        assert a in user_blob and b in user_blob

        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_analyze_case_json_fallback_after_failed_recovery(self):
        """Malformed primary and retry payloads → canonical fallback (foundation contract); audit: json_recovery fallback."""
        mock_client = Mock()
        bogus_primary = Mock()
        bogus_primary.choices = [Mock()]
        bogus_primary.choices[0].message.content = (
            "Invalid JSON response without proper structure"
        )
        bogus_retry = Mock()
        bogus_retry.choices = [Mock()]
        bogus_retry.choices[0].message.content = "{\"classification\": Broken trailing"
        mock_client.chat.completions.create.side_effect = [bogus_primary, bogus_retry]

        logger = ExplainabilityLogger("test_json_error.jsonl")
        agent = RiskAnalystAgent(mock_client, logger)

        customer = CustomerData(
            customer_id="CUST_TEST",
            name="Test Customer",
            date_of_birth="1980-01-01",
            ssn_last_4="1234",
            address="123 Test St",
            customer_since="2020-01-01",
            risk_rating="Low",
        )

        case = CaseData(
            case_id="CASE_ERROR_FALLBACK",
            customer=customer,
            accounts=[],
            transactions=[
                TransactionData(
                    transaction_id="TXN_ERROR",
                    account_id="ACC_ERROR",
                    transaction_date="2025-01-01",
                    transaction_type="Test",
                    amount=100.0,
                    description="Test transaction",
                    method="Test",
                )
            ],
            case_created_at=datetime.now().isoformat(),
            data_sources={"test": "data"},
        )

        canonical = risk_analyst_output_parse_fallback(case.case_id)
        result = agent.analyze_case(case)

        assert isinstance(result, RiskAnalystOutput)
        assert result.model_dump(include={"classification", "confidence_score", "reasoning_steps", "key_indicators", "risk_level"}) == canonical.model_dump(include={"classification", "confidence_score", "reasoning_steps", "key_indicators", "risk_level"})
        assert result.classification == "Other"
        assert "parsing_failed" in result.key_indicators
        assert mock_client.chat.completions.create.call_count == 2

        assert len(logger.entries) == 1
        assert logger.entries[0]["success"] is True
        assert logger.entries[0]["outputs"]["json_recovery"]["path"] == "fallback"

        if os.path.exists("test_json_error.jsonl"):
            os.remove("test_json_error.jsonl")

    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_analyze_case_json_recovery_retry_succeeds(self):
        """Malformed first turn; corrective multimessage retry returns valid RiskAnalystOutput."""
        payload = {
            "classification": "Structuring",
            "confidence_score": 0.85,
            "reasoning_steps": [
                "Reviewed checking account showing repeated deposits under reporting threshold.",
                "Observed clustered cash deposits and round amounts consistent with CTR avoidance.",
                "Mapped indicators to structuring typology referenced under BSA obligations.",
                "High confidence due to sequencing and denomination patterns in source data.",
                "Classification Structuring fits best versus laundering-only or fraud hypotheses.",
            ],
            "key_indicators": ["threshold avoidance", "cash deposits"],
            "risk_level": "High",
        }

        def _msg(content):
            m = Mock()
            m.choices = [Mock()]
            m.choices[0].message.content = content
            return m

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            _msg("Some prose instead of JSON"),
            _msg(json.dumps(payload)),
        ]
        logger = ExplainabilityLogger("test_retry_ok.jsonl")
        agent = RiskAnalystAgent(mock_client, logger)
        customer = CustomerData(
            customer_id="CUST_RETRY",
            name="Retry Customer",
            date_of_birth="1980-01-01",
            ssn_last_4="1234",
            address="1 Retry St",
            customer_since="2020-01-01",
            risk_rating="Low",
        )
        case = CaseData(
            case_id="CASE_RETRY",
            customer=customer,
            accounts=[],
            transactions=[
                TransactionData(
                    transaction_id="TXN_RETRY",
                    account_id="ACC_RETRY",
                    transaction_date="2025-01-01",
                    transaction_type="Test",
                    amount=50.0,
                    description="x",
                    method="Wire",
                )
            ],
            case_created_at=datetime.now().isoformat(),
            data_sources={"retry": "fixture"},
        )
        result = agent.analyze_case(case)
        assert result.classification == "Structuring"
        assert mock_client.chat.completions.create.call_count == 2
        assert logger.entries[-1]["success"] is True
        assert logger.entries[-1]["outputs"]["json_recovery"]["path"] == "retry"

        if os.path.exists("test_retry_ok.jsonl"):
            os.remove("test_retry_ok.jsonl")

    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_analyze_case_fallback_after_valid_json_fails_contract_twice(self):
        """Parsable JSON that violates RiskAnalystOutput (wrong reasoning_steps length) ×2 → fallback fixture."""
        invalid_payload = {
            "classification": "Other",
            "confidence_score": 0.42,
            "reasoning_steps": [
                "Data Review terse.",
                "Pattern Recognition terse.",
                "Regulatory terse.",
            ],
            "key_indicators": ["truncated_contract"],
            "risk_level": "Low",
        }
        stale_json = json.dumps(invalid_payload)

        def _msg(content):
            m = Mock()
            m.choices = [Mock()]
            m.choices[0].message.content = content
            return m

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            _msg(stale_json),
            _msg(stale_json),
        ]
        logger = ExplainabilityLogger(log_file=os.devnull)
        agent = RiskAnalystAgent(mock_client, logger)
        customer = CustomerData(
            customer_id="CUST_BAD_SCHEMA",
            name="Bad Schema Customer",
            date_of_birth="1982-07-07",
            ssn_last_4="9988",
            address="Somewhere Rd",
            customer_since="2018-01-01",
            risk_rating="Low",
        )
        case = CaseData(
            case_id="CASE_BAD_SCHEMA_TWICE",
            customer=customer,
            accounts=[],
            transactions=[
                TransactionData(
                    transaction_id="TX_BAD",
                    account_id="ACC_BAD",
                    transaction_date="2025-05-05",
                    transaction_type="Debit_Purchase",
                    amount=81.05,
                    description="coffee",
                    method="Card",
                )
            ],
            case_created_at=datetime.now().isoformat(),
            data_sources={"fixture": "schema_edge"},
        )
        canonical = risk_analyst_output_parse_fallback(case.case_id)
        result = agent.analyze_case(case)
        assert mock_client.chat.completions.create.call_count == 2
        assert result.reasoning_steps == canonical.reasoning_steps
        assert result.key_indicators == canonical.key_indicators
        assert logger.entries[-1]["outputs"]["json_recovery"]["path"] == "fallback"


    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_analyze_case_recovers_trailing_comma_without_retry(self):
        trailing_comma_blob = (
            '{"classification":"Other","confidence_score":0.42,'
            '"reasoning_steps":["s1","s2","s3","s4","s5"],'
            '"key_indicators":["k"],'
            '"risk_level":"Low",}'
        )
        mock_client = Mock()
        mock_resp = Mock()
        mock_resp.choices = [Mock()]
        mock_resp.choices[0].message.content = trailing_comma_blob
        mock_client.chat.completions.create.return_value = mock_resp
        logger = ExplainabilityLogger("test_trailing_comma.jsonl")
        agent = RiskAnalystAgent(mock_client, logger)
        customer = CustomerData(
            customer_id="CUST_TC",
            name="Comma Customer",
            date_of_birth="1980-01-01",
            ssn_last_4="1234",
            address="Street",
            customer_since="2020-01-01",
            risk_rating="Low",
        )
        case = CaseData(
            case_id="CASE_COMMA",
            customer=customer,
            accounts=[],
            transactions=[
                TransactionData(
                    transaction_id="TXN_TC",
                    account_id="ACC_TC",
                    transaction_date="2025-01-02",
                    transaction_type="Test",
                    amount=10.0,
                    description="d",
                    method="ACH",
                )
            ],
            case_created_at=datetime.now().isoformat(),
            data_sources={"tc": "fixture"},
        )
        result = agent.analyze_case(case)
        assert isinstance(result, RiskAnalystOutput)
        assert mock_client.chat.completions.create.call_count == 1
        assert logger.entries[-1]["outputs"]["json_recovery"]["path"] == "direct"

        if os.path.exists("test_trailing_comma.jsonl"):
            os.remove("test_trailing_comma.jsonl")

    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_extract_json_from_code_block(self):
        """Test JSON extraction from code blocks"""
        agent = RiskAnalystAgent(Mock(), Mock())
        
        response_with_json_block = '''Here is the analysis:
```json
{
    "classification": "Fraud",
    "confidence_score": 0.9,
    "reasoning_steps": ["S1 fraud data review.", "S2 suspicious pattern.", "S3 AML mapping.", "S4 high severity.", "S5 Fraud decision."],
    "key_indicators": ["suspicious_pattern"],
    "risk_level": "Critical"
}
```
That completes the analysis.'''
        
        extracted = agent._extract_json_from_response(response_with_json_block)
        parsed = json.loads(extracted)
        
        assert parsed["classification"] == "Fraud"
        assert parsed["confidence_score"] == 0.9
        assert parsed["risk_level"] == "Critical"
    
    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_extract_json_from_plain_text(self):
        """Test JSON extraction from plain text response"""
        agent = RiskAnalystAgent(Mock(), Mock())
        
        response_plain_json = '''{"classification": "Money_Laundering", "confidence_score": 0.75, "reasoning_steps": ["Step1", "Step2", "Step3", "Step4", "Step5"], "key_indicators": ["multiple_transfers"], "risk_level": "High"}'''
        
        extracted = agent._extract_json_from_response(response_plain_json)
        parsed = json.loads(extracted)
        
        assert parsed["classification"] == "Money_Laundering"
        assert parsed["confidence_score"] == 0.75
    
    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_extract_json_empty_response(self):
        """Test handling of empty LLM response"""
        agent = RiskAnalystAgent(Mock(), Mock())
        
        # Should raise ValueError for empty response
        with pytest.raises(ValueError, match="No JSON content found"):
            agent._extract_json_from_response("")
        
        with pytest.raises(ValueError, match="No JSON content found"):
            agent._extract_json_from_response("   ")
    
    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_format_accounts(self):
        """Test account formatting for prompts"""
        agent = RiskAnalystAgent(Mock(), Mock())
        
        accounts = [
            AccountData(
                account_id="ACC_001",
                customer_id="CUST_001",
                account_type="Checking",
                opening_date="2020-01-01",
                current_balance=15000.50,
                average_monthly_balance=12000.75,
                status="Active"
            ),
            AccountData(
                account_id="ACC_002", 
                customer_id="CUST_001",
                account_type="Savings",
                opening_date="2020-06-01",
                current_balance=25000.00,
                average_monthly_balance=20000.00,
                status="Active"
            )
        ]
        
        formatted = agent._format_accounts(accounts)
        
        assert "ACC_001" in formatted
        assert "Checking" in formatted
        assert "$15,000.50" in formatted
        assert "ACC_002" in formatted
        assert "Savings" in formatted
        assert "$25,000.00" in formatted
    
    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_format_transactions(self):
        """Test transaction formatting for prompts"""
        agent = RiskAnalystAgent(Mock(), Mock())
        
        transactions = [
            TransactionData(
                transaction_id="TXN_001",
                account_id="ACC_001",
                transaction_date="2025-01-01",
                transaction_type="Cash_Deposit",
                amount=9900.0,
                description="Cash deposit at branch",
                method="Cash",
                location="Branch_001"
            ),
            TransactionData(
                transaction_id="TXN_002",
                account_id="ACC_001", 
                transaction_date="2025-01-02",
                transaction_type="Wire_Transfer",
                amount=15000.0,
                description="Wire to offshore account",
                method="Wire"
            )
        ]
        
        formatted = agent._format_transactions(transactions)
        
        assert "1. 2025-01-01: Cash_Deposit $9,900.00" in formatted
        assert "2. 2025-01-02: Wire_Transfer $15,000.00" in formatted
        assert "Cash deposit at branch" in formatted
        assert "Branch_001" in formatted
        assert "Wire to offshore account" in formatted
    
    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_system_prompt_structure(self):
        """Test system prompt contains required elements"""
        agent = RiskAnalystAgent(Mock(), Mock())
        prompt = agent.system_prompt
        
        # Check for stepwise / CoT framing
        assert "reasoning_steps" in prompt
        cot_markers = (
            "Chain-of-Thought",
            "step-by-step",
            "Data Review",
            "Pattern Recognition",
            "five",
        )
        assert any(marker.lower() in prompt.lower() for marker in cot_markers)
        assert "Financial Crime" in prompt or "Risk Analyst" in prompt
        
        # Check for classification categories
        assert "Structuring" in prompt
        assert "Sanctions" in prompt
        assert "Fraud" in prompt
        assert "Money_Laundering" in prompt
        assert "Other" in prompt
        
        # Check for JSON structure requirement
        assert "JSON" in prompt
        assert "classification" in prompt
        assert "confidence_score" in prompt
        assert "reasoning_steps" in prompt
        assert "key_indicators" in prompt
        assert "risk_level" in prompt
        assert "calibration" in prompt.lower()
        assert "0.48" in prompt
    
    @pytest.mark.skipif(not RISK_ANALYST_IMPLEMENTED, reason="Risk Analyst Agent not implemented yet")
    def test_api_call_parameters(self):
        """Test OpenAI API call uses correct parameters"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''{"classification": "Other", "confidence_score": 0.44, "reasoning_steps": ["s1","s2","s3","s4","s5"], "key_indicators": ["test"], "risk_level": "Low"}'''
        mock_client.chat.completions.create.return_value = mock_response
        
        logger = ExplainabilityLogger("test_api.jsonl")
        agent = RiskAnalystAgent(mock_client, logger, model="gpt-3.5-turbo")
        
        # Create minimal case
        customer = CustomerData(
            customer_id="CUST_API",
            name="API Test",
            date_of_birth="1990-01-01", 
            ssn_last_4="9999",
            address="API Test Address",
            customer_since="2021-01-01",
            risk_rating="Low"
        )
        
        case = CaseData(
            case_id="CASE_API",
            customer=customer,
            accounts=[],
            transactions=[TransactionData(
                transaction_id="TXN_API",
                account_id="ACC_API",
                transaction_date="2025-01-01",
                transaction_type="Test",
                amount=1000.0,
                description="API test",
                method="Test"
            )],
            case_created_at=datetime.now().isoformat(),
            data_sources={"api": "test"}
        )
        
        agent.analyze_case(case)
        
        # Verify API call parameters
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-3.5-turbo"
        assert call_args.kwargs["temperature"] == 0.3
        assert call_args.kwargs["max_tokens"] == 1400
        assert len(call_args.kwargs["messages"]) == 2
        assert call_args.kwargs["messages"][0]["role"] == "system"
        assert call_args.kwargs["messages"][1]["role"] == "user"
        
        # Cleanup
        if os.path.exists("test_api.jsonl"):
            os.remove("test_api.jsonl")


def test_risk_analyst_schema_requires_exactly_five_reasoning_steps():
    from pydantic import ValidationError

    try:
        from src.foundation_sar import RiskAnalystOutput
    except ImportError:
        pytest.skip("foundation_sar not available")

    with pytest.raises(ValidationError):
        RiskAnalystOutput(
            classification="Other",
            confidence_score=0.42,
            reasoning_steps=["a", "b"],
            key_indicators=["k"],
            risk_level="Low",
        )

    with pytest.raises(ValidationError):
        RiskAnalystOutput(
            classification="Other",
            confidence_score=0.85,
            reasoning_steps=["a", "b", "c", "d", "e"],
            key_indicators=["k"],
            risk_level="Low",
        )

    out = RiskAnalystOutput(
        classification="Other",
        confidence_score=0.55,
        reasoning_steps=[
            "Data Review: summarized fixture customer and transactions.",
            "Pattern Recognition: no dominant typology; mixed low-signal flows.",
            "Regulatory Mapping: compared to SAR filing guidance generically.",
            "Risk Quantification: moderate residual uncertainty retained.",
            "Classification Decision: Other selected as conservative label.",
        ],
        key_indicators=["mixed_activity"],
        risk_level="Medium",
    )
    assert len(out.reasoning_steps) == 5
    assert "Step 5:" in out.reasoning


@pytest.mark.parametrize(
    "risk_level",
    ["Low", "Medium", "High", "Critical"],
)
def test_risk_calibration_accepts_midpoint_for_each_risk_level(risk_level):
    from src.foundation_sar import RiskAnalystOutput, RISK_LEVEL_CONFIDENCE_BANDS

    lo, hi = RISK_LEVEL_CONFIDENCE_BANDS[risk_level]
    mid = round((lo + hi) / 2, 3)
    RiskAnalystOutput(
        classification="Other",
        confidence_score=mid,
        reasoning_steps=[f"S{i}: align {risk_level} band." for i in range(1, 6)],
        key_indicators=["calibration_fixture"],
        risk_level=risk_level,
    )

