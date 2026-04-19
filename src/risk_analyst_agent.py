# Risk Analyst Agent - Chain-of-Thought Implementation
# TODO: Implement Risk Analyst Agent using Chain-of-Thought prompting

"""
Risk Analyst Agent Module

This agent performs suspicious activity classification using Chain-of-Thought reasoning.
It analyzes customer profiles, account behavior, and transaction patterns to identify
potential financial crimes.

YOUR TASKS:
- Study Chain-of-Thought prompting methodology
- Design system prompt with structured reasoning framework
- Implement case analysis with proper error handling
- Parse and validate structured JSON responses
- Create comprehensive audit logging
"""

import json
import openai
from datetime import datetime, timezone
from typing import Dict, Any, List
from dotenv import load_dotenv

# TODO: Import your foundation components
from src.foundation_sar import (
    RiskAnalystOutput,
    ExplainabilityLogger,
    CaseData,
    AccountData,
    TransactionData,
)

# Load environment variables
load_dotenv()

class RiskAnalystAgent:
    """
    Risk Analyst agent using Chain-of-Thought reasoning.
    
    TODO: Implement agent that:
    - Uses systematic Chain-of-Thought prompting
    - Classifies suspicious activity patterns
    - Returns structured JSON output
    - Handles errors gracefully
    - Logs all operations for audit
    """
    
    def __init__(self, openai_client, explainability_logger, model="gpt-4"):
        """Initialize the Risk Analyst Agent
        
        Args:
            openai_client: OpenAI client instance
            explainability_logger: Logger for audit trails
            model: OpenAI model to use
        """
        # TODO: Initialize agent components
        self.client = openai_client
        self.logger = explainability_logger
        self.model = model
        
        # TODO: Design Chain-of-Thought system prompt
        self.system_prompt = """You are a senior financial crime Risk Analyst.
Use Chain-of-Thought reasoning to analyze each case step-by-step.

Analysis Framework:
1. Data Review: summarize customer, accounts, and transactions.
2. Pattern Recognition: identify suspicious indicators.
3. Regulatory Mapping: map indicators to known typologies.
4. Risk Quantification: assess severity and confidence.
5. Classification Decision: select best category.

Classification categories:
- Structuring
- Sanctions
- Fraud
- Money_Laundering
- Other

Return ONLY valid JSON with this schema:
{
  "classification": "Structuring|Sanctions|Fraud|Money_Laundering|Other",
  "confidence_score": 0.0,
  "reasoning": "step-by-step analysis",
  "key_indicators": ["indicator1", "indicator2"],
  "risk_level": "Low|Medium|High|Critical"
}

Use professional regulatory language. Keep reasoning concise (<=500 chars).
"""

    def analyze_case(self, case_data: CaseData) -> RiskAnalystOutput:
        """
        Perform risk analysis on a case using Chain-of-Thought reasoning.
        
        TODO: Implement analysis that:
        - Creates structured user prompt with case details
        - Makes OpenAI API call with system prompt
        - Parses and validates JSON response
        - Handles errors and logs operations
        - Returns validated RiskAnalystOutput
        """
        start_time = datetime.now(timezone.utc)
        case_prompt = self._format_case_for_prompt(case_data)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": case_prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            content = response.choices[0].message.content or ""
            try:
                json_text = self._extract_json_from_response(content)
                parsed = json.loads(json_text)
                result = RiskAnalystOutput(**parsed)
            except Exception as exc:
                execution_time_ms = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() * 1000
                self.logger.log_agent_action(
                    agent_type="RiskAnalyst",
                    action="analyze_case",
                    case_id=case_data.case_id,
                    input_data={
                        "case_id": case_data.case_id,
                        "accounts": len(case_data.accounts),
                        "transactions": len(case_data.transactions),
                    },
                    output_data={},
                    reasoning="JSON parsing failed during risk analysis.",
                    execution_time_ms=execution_time_ms,
                    success=False,
                    error_message=str(exc),
                )
                raise ValueError("Failed to parse Risk Analyst JSON output") from exc
            execution_time_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            self.logger.log_agent_action(
                agent_type="RiskAnalyst",
                action="analyze_case",
                case_id=case_data.case_id,
                input_data={
                    "case_id": case_data.case_id,
                    "accounts": len(case_data.accounts),
                    "transactions": len(case_data.transactions),
                },
                output_data=result.model_dump(),
                reasoning=result.reasoning,
                execution_time_ms=execution_time_ms,
            )
            return result
        except ValueError:
            raise
        except Exception as exc:
            execution_time_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            self.logger.log_agent_action(
                agent_type="RiskAnalyst",
                action="analyze_case",
                case_id=case_data.case_id,
                input_data={
                    "case_id": case_data.case_id,
                    "accounts": len(case_data.accounts),
                    "transactions": len(case_data.transactions),
                },
                output_data={},
                reasoning="Risk analysis failed; see error message.",
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(exc),
            )
            raise

    def _extract_json_from_response(self, response_content: str) -> str:
        """Extract JSON content from LLM response
        
        TODO: Implement JSON extraction that handles:
        - JSON in code blocks (```json)
        - JSON in plain text
        - Malformed responses
        - Empty responses
        """
        content = response_content.strip()
        if not content:
            raise ValueError("No JSON content found")

        if "```" in content:
            start = content.find("```json")
            if start != -1:
                start += len("```json")
            else:
                start = content.find("```") + len("```")
            end = content.find("```", start)
            if end == -1:
                raise ValueError("Unterminated JSON code block")
            json_candidate = content[start:end].strip()
            if json_candidate:
                return json_candidate

        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON content found")
        return content[start : end + 1]

    def _format_accounts(self, accounts: List[AccountData]) -> str:
        if not accounts:
            return "No accounts available."
        lines = []
        for account in accounts:
            lines.append(
                "Account {account_id} ({account_type}): Current Balance {balance}, "
                "Avg Monthly {avg_balance}, Status {status}".format(
                    account_id=account.account_id,
                    account_type=account.account_type,
                    balance=f"${account.current_balance:,.2f}",
                    avg_balance=f"${account.average_monthly_balance:,.2f}",
                    status=account.status,
                )
            )
        return "\n".join(lines)

    def _format_transactions(self, transactions: List[TransactionData]) -> str:
        if not transactions:
            return "No transactions available."
        lines = []
        for idx, txn in enumerate(transactions, start=1):
            amount = f"${txn.amount:,.2f}"
            line = f"{idx}. {txn.transaction_date}: {txn.transaction_type} {amount}"
            details = [txn.description, f"Method: {txn.method}"]
            if txn.location:
                details.append(f"Location: {txn.location}")
            line += " - " + ", ".join(details)
            lines.append(line)
        return "\n".join(lines)

    def _format_case_for_prompt(self, case_data) -> str:
        """Format case data for the analysis prompt
        
        TODO: Create readable prompt format that includes:
        - Customer profile summary
        - Account information
        - Transaction details with key metrics
        - Financial summary statistics
        """
        transaction_count = len(case_data.transactions)
        total_amount = sum(txn.amount for txn in case_data.transactions)
        avg_amount = total_amount / transaction_count if transaction_count else 0.0
        account_summary = self._format_accounts(case_data.accounts)
        transaction_summary = self._format_transactions(case_data.transactions[:5])

        return (
            "Case Summary:\n"
            f"Case ID: {case_data.case_id}\n\n"
            "Customer Profile:\n"
            f"- Name: {case_data.customer.name}\n"
            f"- Customer ID: {case_data.customer.customer_id}\n"
            f"- Risk Rating: {case_data.customer.risk_rating}\n"
            f"- Customer Since: {case_data.customer.customer_since}\n\n"
            "Accounts:\n"
            + account_summary
            + "\n\n"
            "Transactions (first 5):\n"
            f"{transaction_summary}\n\n"
            "Transaction Metrics:\n"
            f"- Total transactions: {transaction_count}\n"
            f"- Total amount: {total_amount}\n"
            f"- Average amount: {avg_amount:.2f}\n"
        )

# ===== PROMPT ENGINEERING HELPERS =====

def create_chain_of_thought_framework():
    """Helper function showing Chain-of-Thought structure
    
    TODO: Study this example and adapt for financial crime analysis:
    
    **Analysis Framework** (Think step-by-step):
    1. **Data Review**: What does the data tell us?
    2. **Pattern Recognition**: What patterns are suspicious?
    3. **Regulatory Mapping**: Which regulations apply?
    4. **Risk Quantification**: How severe is the risk?
    5. **Classification Decision**: What category fits best?
    """
    return {
        "step_1": "Data Review - Examine all available information",
        "step_2": "Pattern Recognition - Identify suspicious indicators", 
        "step_3": "Regulatory Mapping - Connect to known typologies",
        "step_4": "Risk Quantification - Assess severity level",
        "step_5": "Classification Decision - Determine final category"
    }

def get_classification_categories():
    """Standard SAR classification categories
    
    TODO: Use these categories in your prompts:
    """
    return {
        "Structuring": "Transactions designed to avoid reporting thresholds",
        "Sanctions": "Potential sanctions violations or prohibited parties",
        "Fraud": "Fraudulent transactions or identity-related crimes",
        "Money_Laundering": "Complex schemes to obscure illicit fund sources", 
        "Other": "Suspicious patterns not fitting standard categories"
    }

# ===== TESTING UTILITIES =====

def test_agent_with_sample_case():
    """Test the agent with a sample case
    
    TODO: Use this function to test your implementation:
    - Create sample case data
    - Initialize agent
    - Run analysis
    - Validate results
    """
    print("🧪 Testing Risk Analyst Agent")
    print("TODO: Implement test case")

if __name__ == "__main__":
    print("🔍 Risk Analyst Agent Module")
    print("Chain-of-Thought reasoning for suspicious activity classification")
    print("\n📋 TODO Items:")
    print("• Design Chain-of-Thought system prompt")
    print("• Implement analyze_case method")
    print("• Add JSON parsing and validation")
    print("• Create comprehensive error handling")
    print("• Test with sample cases")
    print("\n💡 Key Concepts:")
    print("• Chain-of-Thought: Step-by-step reasoning")
    print("• Structured Output: Validated JSON responses")
    print("• Financial Crime Detection: Pattern recognition")
    print("• Audit Logging: Complete decision trails")
