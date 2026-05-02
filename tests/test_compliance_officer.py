"""
Tests for Compliance Officer Agent

The Compliance Officer Agent is responsible for generating regulatory-compliant SAR narratives
using the ReACT (Reasoning-Action-Conclusion-Thought) prompting framework. The agent must:
- Generate concise narratives (≤120 words)
- Include proper regulatory citations
- Apply BSA/AML compliance expertise
- Format outputs for FinCEN SAR submission

This test suite validates the compliance narrative generation functionality.
"""

import pytest
import json
import os
from datetime import datetime
from unittest.mock import Mock

# Import source code directly from starter module
from src.compliance_officer_agent import ComplianceOfficerAgent
from src.foundation_sar import (
    CustomerData, AccountData, TransactionData, CaseData,
    ComplianceOfficerOutput, RiskAnalystOutput, ExplainabilityLogger
)

_SAMPLE_RISK_COT_STEPS = [
    "Data review: verified customer profile, accounts, and transactions in fixture.",
    "Pattern recognition: linked activity to structuring-like threshold behavior.",
    "Regulatory mapping: considered BSA/CTR and SAR filing expectations.",
    "Risk quantification: confidence reflects strength of patterned activity.",
    "Classification decision: Structuring aligns best with summarized indicators.",
]

# Skip detection - Check if compliance officer has real implementation
try:
    # Try to create a test instance to see if the class is implemented
    test_client = Mock()
    test_logger = Mock()
    test_agent = ComplianceOfficerAgent(test_client, test_logger)
    
    # Check for actual implementation vs placeholder
    has_real_prompt = (hasattr(test_agent, 'system_prompt') and 
                      test_agent.system_prompt is not None and
                      "TODO" not in str(test_agent.system_prompt) and
                      len(str(test_agent.system_prompt)) > 200)
    
    has_generate_method = hasattr(test_agent, 'generate_compliance_narrative')
    
    # Check if generate_compliance_narrative is implemented (not just 'pass')
    if has_generate_method:
        import inspect
        source = inspect.getsource(test_agent.generate_compliance_narrative)
        method_implemented = not ('pass' in source and source.count('\n') < 10)
    else:
        method_implemented = False
    
    # Check if agent has required attributes that indicate real implementation
    has_client_attr = hasattr(test_agent, 'client')
    has_logger_attr = hasattr(test_agent, 'logger')
    
    COMPLIANCE_OFFICER_IMPLEMENTED = (has_real_prompt and has_generate_method and 
                                    method_implemented and has_client_attr and has_logger_attr)
    
except Exception:
    # If we can't import or instantiate, mark as not implemented
    COMPLIANCE_OFFICER_IMPLEMENTED = False


class TestComplianceOfficerAgent:
    """Test ComplianceOfficerAgent core functionality"""
    
    @pytest.mark.skipif(not COMPLIANCE_OFFICER_IMPLEMENTED, reason="Compliance Officer Agent not implemented yet")
    def test_agent_initialization(self):
        """Test ComplianceOfficerAgent initializes properly"""
        mock_client = Mock()
        logger = ExplainabilityLogger("test_compliance.jsonl")
        
        agent = ComplianceOfficerAgent(mock_client, logger, model="gpt-4")
        
        assert agent.client == mock_client
        assert agent.logger == logger
        assert agent.model == "gpt-4"
        assert agent.system_prompt is not None
        assert len(agent.system_prompt) > 200  # Should have substantial ReACT prompt
        
        # Cleanup
        if os.path.exists("test_compliance.jsonl"):
            os.remove("test_compliance.jsonl")
    
    @pytest.mark.skipif(not COMPLIANCE_OFFICER_IMPLEMENTED, reason="Compliance Officer Agent not implemented yet")
    def test_generate_compliance_narrative_success(self):
        """Test successful narrative generation with valid response"""
        # Setup mock OpenAI client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
{
    "narrative": "Customer John Doe (CUST_001) surfaced suspicious activity on 2025-01-01 and 2025-01-02 when repeated Cash_Deposit transactions totaled $29,500 across $9,900, $9,800, and $9,800 amounts designed under a Regulatory threshold to stress our Financial institution monitoring. Threshold avoidance indicators and repeated amounts raise patterns consistent with money laundering structuring risk under Bank Secrecy Act expectations referencing 31 USC 5324, 31 CFR 1020.320 SAR duties, plus FinCEN SAR Instructions escalation language.",
    "narrative_reasoning": "Quantified structuring sequence with calibrated analyst indicators and echoed regulatory citations.",
    "regulatory_citations": ["31 USC 5324 (Structuring bar)", "31 CFR 1020.320 (SAR filings)", "FinCEN SAR Instructions"],
    "completeness_check": false
}
```'''
        mock_client.chat.completions.create.return_value = mock_response
        
        # Setup logger
        logger = ExplainabilityLogger("test_narrative.jsonl")
        agent = ComplianceOfficerAgent(mock_client, logger)
        
        # Create test case data
        customer = CustomerData(
            customer_id="CUST_001",
            name="John Doe",
            date_of_birth="1980-01-01",
            ssn_last_4="1234",
            address="123 Main St",
            customer_since="2020-01-01",
            risk_rating="Medium"
        )
        
        account = AccountData(
            account_id="ACC_001",
            customer_id="CUST_001",
            account_type="Checking",
            opening_date="2020-01-01",
            current_balance=15000.0,
            average_monthly_balance=12000.0,
            status="Active"
        )
        
        transactions = [
            TransactionData(
                transaction_id="TXN_001",
                account_id="ACC_001",
                transaction_date="2025-01-01",
                transaction_type="Cash_Deposit",
                amount=9900.0,
                description="Cash deposit",
                method="Cash"
            ),
            TransactionData(
                transaction_id="TXN_002",
                account_id="ACC_001",
                transaction_date="2025-01-02",
                transaction_type="Cash_Deposit",
                amount=9800.0,
                description="Cash deposit",
                method="Cash"
            )
        ]
        
        case = CaseData(
            case_id="CASE_001",
            customer=customer,
            accounts=[account],
            transactions=transactions,
            case_created_at=datetime.now().isoformat(),
            data_sources={"test": "data"}
        )
        
        # Create risk analysis input
        risk_analysis = RiskAnalystOutput(
            classification="Structuring",
            confidence_score=0.85,
            reasoning_steps=_SAMPLE_RISK_COT_STEPS,
            key_indicators=["threshold avoidance", "repeated amounts"],
            risk_level="High"
        )
        
        # Run narrative generation
        result = agent.generate_compliance_narrative(case, risk_analysis)
        
        # Verify result
        assert isinstance(result, ComplianceOfficerOutput)
        assert "John Doe" in result.narrative
        assert "structuring" in result.narrative.lower() or "threshold" in result.narrative.lower()
        assert len(result.narrative.split()) <= 120  # Word count check
        assert result.completeness_check == True  # deterministic QA overrides model flag
        assert len(result.regulatory_citations) > 0
        
        # Verify API was called
        mock_client.chat.completions.create.assert_called_once()
        
        # Verify logging
        assert len(logger.entries) == 1
        assert logger.entries[0]["success"] == True
        assert logger.entries[0]["agent_type"] == "ComplianceOfficer"
        
        # Cleanup
        if os.path.exists("test_narrative.jsonl"):
            os.remove("test_narrative.jsonl")
    
    @pytest.mark.skipif(not COMPLIANCE_OFFICER_IMPLEMENTED, reason="Compliance Officer Agent not implemented yet")
    def test_narrative_word_count_validation(self):
        """Test narrative word count validation (120 word limit)"""
        # Setup mock with overly long narrative
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # Create a narrative with more than 120 words
        long_narrative = " ".join(["word"] * 150)  # 150 words
        mock_response.choices[0].message.content = f'''{{
    "narrative": "{long_narrative}",
    "narrative_reasoning": "Test reasoning",
    "regulatory_citations": ["31 CFR 1020.320"],
    "completeness_check": true
}}'''
        mock_client.chat.completions.create.return_value = mock_response
        
        logger = ExplainabilityLogger("test_wordcount.jsonl")
        agent = ComplianceOfficerAgent(mock_client, logger)
        
        # Create minimal test data
        customer = CustomerData(
            customer_id="CUST_TEST",
            name="Test Customer",
            date_of_birth="1980-01-01",
            ssn_last_4="1234",
            address="123 Test St",
            customer_since="2020-01-01",
            risk_rating="Low"
        )
        
        case = CaseData(
            case_id="CASE_WORDCOUNT",
            customer=customer,
            accounts=[],
            transactions=[TransactionData(
                transaction_id="TXN_TEST",
                account_id="ACC_TEST",
                transaction_date="2025-01-01",
                transaction_type="Test",
                amount=1000.0,
                description="Test transaction",
                method="Test"
            )],
            case_created_at=datetime.now().isoformat(),
            data_sources={"test": "data"}
        )
        
        risk_analysis = RiskAnalystOutput(
            classification="Other",
            confidence_score=0.44,
            reasoning_steps=[
                "Data review: placeholder test case.",
                "Pattern recognition: no strong typology match.",
                "Regulatory mapping: general SAR context only.",
                "Risk quantification: moderate uncertainty.",
                "Classification decision: Other.",
            ],
            key_indicators=["test"],
            risk_level="Low"
        )
        
        # Deterministic SAR QA surfaces word-limit breach (wording varies with QA messages).
        with pytest.raises(ValueError, match=r"120 word"):
            agent.generate_compliance_narrative(case, risk_analysis)
        
        # Cleanup
        if os.path.exists("test_wordcount.jsonl"):
            os.remove("test_wordcount.jsonl")
    
    @pytest.mark.skipif(not COMPLIANCE_OFFICER_IMPLEMENTED, reason="Compliance Officer Agent not implemented yet")
    def test_json_parsing_error_degrades_with_fallback(self):
        """Malformed JSON twice yields ComplianceOfficerOutput fallback so workflow proceeds."""
        # Setup mock with invalid JSON
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON response without proper structure"
        mock_client.chat.completions.create.return_value = mock_response
        
        logger = ExplainabilityLogger("test_json_error.jsonl")
        agent = ComplianceOfficerAgent(mock_client, logger)
        
        # Create minimal test case
        customer = CustomerData(
            customer_id="CUST_ERROR",
            name="Error Customer",
            date_of_birth="1980-01-01",
            ssn_last_4="1234",
            address="123 Error St",
            customer_since="2020-01-01",
            risk_rating="Low"
        )
        
        case = CaseData(
            case_id="CASE_ERROR",
            customer=customer,
            accounts=[],
            transactions=[TransactionData(
                transaction_id="TXN_ERROR",
                account_id="ACC_ERROR",
                transaction_date="2025-01-01",
                transaction_type="Test",
                amount=100.0,
                description="Error test",
                method="Test"
            )],
            case_created_at=datetime.now().isoformat(),
            data_sources={"test": "data"}
        )
        
        risk_analysis = RiskAnalystOutput(
            classification="Other",
            confidence_score=0.3,
            reasoning_steps=[
                "Data review: minimal error-path fixture.",
                "Pattern recognition: not evaluated.",
                "Regulatory mapping: not evaluated.",
                "Risk quantification: low emphasis.",
                "Classification decision: Other for test.",
            ],
            key_indicators=["error"],
            risk_level="Low"
        )
        
        bad = mock_response
        mock_client.chat.completions.create.return_value = bad
        result = agent.generate_compliance_narrative(case, risk_analysis)

        assert isinstance(result, ComplianceOfficerOutput)
        assert result.completeness_check is False
        assert "parsing_failed" in result.narrative.lower()
        assert mock_client.chat.completions.create.call_count == 2

        assert len(logger.entries) == 1
        assert logger.entries[0]["success"] is True
        assert logger.entries[0]["outputs"]["json_recovery"]["path"] == "fallback"
        
        # Cleanup
        if os.path.exists("test_json_error.jsonl"):
            os.remove("test_json_error.jsonl")

    @pytest.mark.skipif(not COMPLIANCE_OFFICER_IMPLEMENTED, reason="Compliance Officer Agent not implemented yet")
    def test_json_recovery_retry_succeeds(self):
        good = {
            "narrative": (
                "Retry Co (CUST_CO_RETRY) is the SAR subject flagged for suspicious activity on 2025-03-01 after a fixture "
                "$500 wire that highlights threshold-like behavior monitored by our Financial institution. Narrative echoes "
                "fixture indicators and underscores Money laundering preparedness, citing the Regulatory threshold discussion "
                "plus Bank Secrecy Act supervisory expectations referencing 31 CFR 1020.320 SAR filing language and repeated "
                "FinCEN SAR Instructions mandates (also noting potential pattern risk)."
            ),
            "narrative_reasoning": "Structured recovery-turn narrative aligning fixture indicators.",
            "regulatory_citations": ["31 CFR 1020.320 (Bank Secrecy Act SAR duties)", "FinCEN SAR Instructions"],
            "completeness_check": False,
        }

        def _msg(content):
            m = Mock()
            m.choices = [Mock()]
            m.choices[0].message.content = content
            return m

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            _msg("Not JSON."),
            _msg(json.dumps(good)),
        ]
        logger = ExplainabilityLogger("test_co_retry.jsonl")
        agent = ComplianceOfficerAgent(mock_client, logger)
        customer = CustomerData(
            customer_id="CUST_CO_RETRY",
            name="Retry Co",
            date_of_birth="1980-01-01",
            ssn_last_4="1234",
            address="Address",
            customer_since="2020-01-01",
            risk_rating="Low",
        )
        case = CaseData(
            case_id="CASE_CORETRY",
            customer=customer,
            accounts=[],
            transactions=[
                TransactionData(
                    transaction_id="TXN_CR",
                    account_id="ACC_CR",
                    transaction_date="2025-03-01",
                    transaction_type="Wire",
                    amount=500.0,
                    description="d",
                    method="Wire",
                )
            ],
            case_created_at=datetime.now().isoformat(),
            data_sources={"retry": "fixture"},
        )
        risk_analysis = RiskAnalystOutput(
            classification="Other",
            confidence_score=0.42,
            reasoning_steps=[
                "Data Review: Fixture.",
                "Pattern Recognition: Fixture.",
                "Regulatory Mapping: Fixture.",
                "Risk Quantification: Fixture.",
                "Classification Decision: Other.",
            ],
            key_indicators=["fixture"],
            risk_level="Low",
        )
        result = agent.generate_compliance_narrative(case, risk_analysis)
        assert result.completeness_check is True
        assert mock_client.chat.completions.create.call_count == 2
        assert logger.entries[-1]["outputs"]["json_recovery"]["path"] == "retry"

        if os.path.exists("test_co_retry.jsonl"):
            os.remove("test_co_retry.jsonl")

    @pytest.mark.skipif(not COMPLIANCE_OFFICER_IMPLEMENTED, reason="Compliance Officer Agent not implemented yet")
    def test_deterministic_sar_validation_rejects_partial_output(self):
        """LLM completeness_check=true does not waive mandated terminology / structure."""
        nar = (
            "API Test Customer (CUST_API) flagged suspicious deposits on 2025-01-01 tying to test SAR monitoring with "
            "$1,010 across transactions and threshold avoidance chatter citing 31 CFR 1020.320 SAR text plus Bank Secrecy Act "
            "obligations, but skips several mandated phrases auditors require."
        )
        mock_payload = json.dumps(
            {
                "narrative": nar,
                "narrative_reasoning": "LLM falsely marked complete.",
                "regulatory_citations": ["31 CFR 1020.320 SAR narrative duties", "FinCEN SAR Instructions"],
                "completeness_check": True,
            }
        )

        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = mock_payload
        mock_client.chat.completions.create.return_value = mock_response

        logger = ExplainabilityLogger("test_sar_gate.jsonl")
        agent = ComplianceOfficerAgent(mock_client, logger)

        customer = CustomerData(
            customer_id="CUST_API",
            name="API Test Customer",
            date_of_birth="1990-01-01",
            ssn_last_4="9999",
            address="API Addr",
            customer_since="2021-01-01",
            risk_rating="Low",
        )
        case = CaseData(
            case_id="CASE_GATE",
            customer=customer,
            accounts=[],
            transactions=[
                TransactionData(
                    transaction_id="TXN_GATE",
                    account_id="ACC_GATE",
                    transaction_date="2025-01-01",
                    transaction_type="Deposit",
                    amount=1010.0,
                    description="gate",
                    method="ACH",
                )
            ],
            case_created_at=datetime.now().isoformat(),
            data_sources={"gate": "test"},
        )
        risk_analysis = RiskAnalystOutput(
            classification="Other",
            confidence_score=0.42,
            reasoning_steps=list(_SAMPLE_RISK_COT_STEPS),
            key_indicators=["threshold avoidance"],
            risk_level="Low",
        )

        with pytest.raises(ValueError, match="SAR deterministic validation"):
            agent.generate_compliance_narrative(case, risk_analysis)

        if os.path.exists("test_sar_gate.jsonl"):
            os.remove("test_sar_gate.jsonl")

    @pytest.mark.skipif(not COMPLIANCE_OFFICER_IMPLEMENTED, reason="Compliance Officer Agent not implemented yet")
    def test_extract_json_from_code_block(self):
        """Test JSON extraction from code blocks"""
        agent = ComplianceOfficerAgent(Mock(), Mock())
        
        response_with_json_block = '''Here is the compliance narrative:
```json
{
    "narrative": "Test narrative for compliance validation",
    "narrative_reasoning": "Generated for testing purposes",
    "regulatory_citations": ["31 CFR 1020.320"],
    "completeness_check": true
}
```
This completes the analysis.'''
        
        extracted = agent._extract_json_from_response(response_with_json_block)
        parsed = json.loads(extracted)
        
        assert parsed["narrative"] == "Test narrative for compliance validation"
        assert parsed["completeness_check"] == True
        assert "31 CFR 1020.320" in parsed["regulatory_citations"]
    
    @pytest.mark.skipif(not COMPLIANCE_OFFICER_IMPLEMENTED, reason="Compliance Officer Agent not implemented yet")
    def test_extract_json_from_plain_text(self):
        """Test JSON extraction from plain text response"""
        agent = ComplianceOfficerAgent(Mock(), Mock())
        
        response_plain_json = '''{"narrative": "Plain text compliance narrative", "narrative_reasoning": "Simple extraction test", "regulatory_citations": ["BSA Requirements"], "completeness_check": false}'''
        
        extracted = agent._extract_json_from_response(response_plain_json)
        parsed = json.loads(extracted)
        
        assert parsed["narrative"] == "Plain text compliance narrative"
        assert parsed["completeness_check"] == False
    
    @pytest.mark.skipif(not COMPLIANCE_OFFICER_IMPLEMENTED, reason="Compliance Officer Agent not implemented yet")
    def test_extract_json_empty_response(self):
        """Test handling of empty LLM response"""
        agent = ComplianceOfficerAgent(Mock(), Mock())
        
        # Should raise ValueError for empty response
        with pytest.raises(ValueError, match="No JSON content found"):
            agent._extract_json_from_response("")
        
        with pytest.raises(ValueError, match="No JSON content found"):
            agent._extract_json_from_response("   ")
    
    @pytest.mark.skipif(not COMPLIANCE_OFFICER_IMPLEMENTED, reason="Compliance Officer Agent not implemented yet")
    def test_format_transactions_for_compliance(self):
        """Test transaction formatting for compliance narratives"""
        agent = ComplianceOfficerAgent(Mock(), Mock())
        
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
                description="Wire to suspicious account",
                method="Wire"
            )
        ]
        
        formatted = agent._format_transactions_for_compliance(transactions)
        
        assert "1. 2025-01-01: $9,900.00 Cash_Deposit" in formatted
        assert "2. 2025-01-02: $15,000.00 Wire_Transfer" in formatted
        assert "at Branch_001" in formatted
        assert "via Wire" in formatted
    
    @pytest.mark.skipif(not COMPLIANCE_OFFICER_IMPLEMENTED, reason="Compliance Officer Agent not implemented yet")
    def test_system_prompt_structure(self):
        """Test system prompt contains required ReACT elements"""
        agent = ComplianceOfficerAgent(Mock(), Mock())
        prompt = agent.system_prompt
        
        # Check for ReACT framework elements
        assert "ReACT" in prompt or "REASONING" in prompt
        assert "Compliance Officer" in prompt
        assert "BSA/AML" in prompt
        
        # Check for narrative requirements
        assert "120 words" in prompt or "word limit" in prompt
        assert "FinCEN" in prompt or "SAR" in prompt
        
        # Check for JSON structure requirement
        assert "JSON" in prompt
        assert "narrative" in prompt
        assert "narrative_reasoning" in prompt
        assert "regulatory_citations" in prompt
        assert "completeness_check" in prompt
    
    @pytest.mark.skipif(not COMPLIANCE_OFFICER_IMPLEMENTED, reason="Compliance Officer Agent not implemented yet")
    def test_api_call_parameters(self):
        """Test OpenAI API call uses correct parameters"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''{"narrative": "API Test Customer (CUST_API) exhibits suspicious activity on 2025-01-01 when the ACH transfer records $1,000.00; threshold avoidance aligns with Regulatory threshold monitoring at our Financial institution and raises elevated concern tied to Money laundering typologies under Bank Secrecy Act review echoing analysts test indicator language plus 31 CFR 1020.320 SAR filing duties and repeated FinCEN SAR Instructions supervisory expectations demonstrating potential structuring risk.", "narrative_reasoning": "API smoke narrative auto-pass checks.", "regulatory_citations": ["31 CFR 1020.320 (SAR supervisory duties)", "FinCEN SAR Instructions"], "completeness_check": false}'''
        mock_client.chat.completions.create.return_value = mock_response
        
        logger = ExplainabilityLogger("test_api_compliance.jsonl")
        agent = ComplianceOfficerAgent(mock_client, logger, model="gpt-3.5-turbo")
        
        # Create minimal case and risk analysis
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
        
        risk_analysis = RiskAnalystOutput(
            classification="Other",
            confidence_score=0.44,
            reasoning_steps=list(_SAMPLE_RISK_COT_STEPS),
            key_indicators=["test"],
            risk_level="Low"
        )
        
        agent.generate_compliance_narrative(case, risk_analysis)
        
        # Verify API call parameters
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-3.5-turbo"
        assert call_args.kwargs["temperature"] == 0.2  # Lower temperature for compliance
        assert call_args.kwargs["max_tokens"] == 800
        assert len(call_args.kwargs["messages"]) == 2
        assert call_args.kwargs["messages"][0]["role"] == "system"
        assert call_args.kwargs["messages"][1]["role"] == "user"
        
        # Cleanup
        if os.path.exists("test_api_compliance.jsonl"):
            os.remove("test_api_compliance.jsonl")
