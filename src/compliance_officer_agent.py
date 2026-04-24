# Compliance Officer Agent - ReACT Implementation  
# TODO: Implement Compliance Officer Agent using ReACT prompting

"""
Compliance Officer Agent Module

This agent generates regulatory-compliant SAR narratives using ReACT prompting.
It takes risk analysis results and creates structured documentation for 
FinCEN submission.

YOUR TASKS:
- Study ReACT (Reasoning + Action) prompting methodology
- Design system prompt with Reasoning/Action framework
- Implement narrative generation with word limits
- Validate regulatory compliance requirements
- Create proper audit logging and error handling
"""

import json
import openai
from datetime import datetime, timezone
from typing import Dict, Any, List
from dotenv import load_dotenv

# TODO: Import your foundation components
from src.foundation_sar import (
    ComplianceOfficerOutput,
    ExplainabilityLogger,
    CaseData,
    RiskAnalystOutput,
    TransactionData,
)

# Load environment variables
load_dotenv()

class ComplianceOfficerAgent:
    """
    Compliance Officer agent using ReACT prompting framework.
    
    TODO: Implement agent that:
    - Uses Reasoning + Action structured prompting
    - Generates regulatory-compliant SAR narratives
    - Enforces word limits and terminology
    - Includes regulatory citations
    - Validates narrative completeness
    """
    
    def __init__(self, openai_client, explainability_logger, model="gpt-4"):
        """Initialize the Compliance Officer Agent
        
        Args:
            openai_client: OpenAI client instance
            explainability_logger: Logger for audit trails
            model: OpenAI model to use
        """
        # TODO: Initialize agent components
        self.client = openai_client
        self.logger = explainability_logger
        self.model = model
        
        # TODO: Design ReACT system prompt
        self.system_prompt = """You are a senior Compliance Officer responsible for SAR narratives.
Use the ReACT framework (Reasoning + Action) to produce a compliant narrative.
This must align with BSA/AML expectations and FinCEN SAR requirements.

REACT Framework:
REASONING:
1. Review the Risk Analyst findings.
2. Identify regulatory requirements and narrative elements.
3. Determine key suspicious activity details (who/what/when/where/why).
4. Plan concise narrative structure.

ACTION:
1. Draft the SAR narrative (<=120 words).
2. Include specific dates, amounts, and patterns.
3. Use regulatory terminology (BSA/AML, SAR, suspicious activity).
4. Provide citations where relevant.

Return ONLY valid JSON with this schema:
{
  "narrative": "SAR narrative text (<=120 words)",
  "narrative_reasoning": "Why this narrative meets compliance needs",
  "regulatory_citations": ["citation1", "citation2"],
  "completeness_check": true
}
"""

    def generate_compliance_narrative(self, case_data, risk_analysis) -> 'ComplianceOfficerOutput':
        """
        Generate regulatory-compliant SAR narrative using ReACT framework.
        
        TODO: Implement narrative generation that:
        - Creates ReACT-structured user prompt
        - Includes risk analysis findings
        - Makes OpenAI API call with constraints
        - Validates narrative word count
        - Parses and validates JSON response
        - Logs operations for audit
        """
        start_time = datetime.now(timezone.utc)
        risk_summary = self._format_risk_analysis_for_prompt(risk_analysis)
        transaction_summary = self._format_transactions_for_compliance(case_data.transactions)
        prompt = (
            "Case Context:\n"
            f"Customer: {case_data.customer.name} ({case_data.customer.customer_id})\n"
            f"Risk Rating: {case_data.customer.risk_rating}\n\n"
            "Risk Analysis Summary:\n"
            f"{risk_summary}\n\n"
            "Transactions:\n"
            f"{transaction_summary}\n"
        )

        try:
            response = self._request_completion(prompt)
            content = response.choices[0].message.content or ""
            try:
                json_text = self._extract_json_from_response(content)
                parsed = json.loads(json_text)
                result = ComplianceOfficerOutput(**parsed)
            except Exception as exc:
                retry_prompt = (
                    "Return ONLY valid JSON that matches the required schema. "
                    "Do not include code fences or commentary.\n\n"
                    + prompt
                )
                try:
                    content = self._request_completion(retry_prompt).choices[0].message.content or ""
                    json_text = self._extract_json_from_response(content)
                    parsed = json.loads(json_text)
                    result = ComplianceOfficerOutput(**parsed)
                except Exception:
                    execution_time_ms = (
                        datetime.now(timezone.utc) - start_time
                    ).total_seconds() * 1000
                    fallback = self._build_fallback_output()
                    self.logger.log_agent_action(
                        agent_type="ComplianceOfficer",
                        action="generate_narrative",
                        case_id=case_data.case_id,
                        input_data={"case_id": case_data.case_id},
                        output_data=fallback.model_dump(),
                        reasoning="Parsing failed; fallback output returned.",
                        execution_time_ms=execution_time_ms,
                        success=False,
                        error_message=str(exc),
                    )
                    return fallback

            compliance_check = self._validate_narrative_compliance(
                result.narrative, result.regulatory_citations
            )
            if not compliance_check["within_word_limit"]:
                raise ValueError("Narrative exceeds 120 word limit")
            if not compliance_check["is_complete"]:
                missing = ", ".join(compliance_check["missing_elements"])
                raise ValueError(f"Narrative missing required elements: {missing}")

            result = result.model_copy(
                update={"completeness_check": compliance_check["is_complete"]}
            )

            execution_time_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            self.logger.log_agent_action(
                agent_type="ComplianceOfficer",
                action="generate_narrative",
                case_id=case_data.case_id,
                input_data={"case_id": case_data.case_id},
                output_data=result.model_dump(),
                reasoning=result.narrative_reasoning,
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
                agent_type="ComplianceOfficer",
                action="generate_narrative",
                case_id=case_data.case_id,
                input_data={"case_id": case_data.case_id},
                output_data={},
                reasoning="Compliance narrative generation failed; see error message.",
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(exc),
            )
            raise

    def _request_completion(self, prompt: str):
        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=800,
        )

    def _build_fallback_output(self) -> ComplianceOfficerOutput:
        return ComplianceOfficerOutput(
            narrative="Parsing failed; manual review required.",
            narrative_reasoning="Fallback narrative used due to parsing failure.",
            regulatory_citations=[],
            completeness_check=False,
        )

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
                raise ValueError("No JSON content found")
            json_candidate = content[start:end].strip()
            if json_candidate:
                return json_candidate

        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON content found")
        return content[start : end + 1]

    def _format_risk_analysis_for_prompt(self, risk_analysis) -> str:
        """Format risk analysis results for compliance prompt
        
        TODO: Create structured format that includes:
        - Classification and confidence
        - Key suspicious indicators
        - Risk level assessment
        - Analyst reasoning
        """
        return (
            "Classification: {classification}\n"
            "Confidence: {confidence:.2f}\n"
            "Risk Level: {risk_level}\n"
            "Key Indicators: {indicators}\n"
            "Reasoning: {reasoning}".format(
                classification=risk_analysis.classification,
                confidence=risk_analysis.confidence_score,
                risk_level=risk_analysis.risk_level,
                indicators=", ".join(risk_analysis.key_indicators),
                reasoning=risk_analysis.reasoning,
            )
        )

    def _validate_narrative_compliance(
        self, narrative: str, citations: List[str]
    ) -> Dict[str, Any]:
        """Validate narrative meets regulatory requirements
        
        TODO: Implement validation that checks:
        - Word count (≤120 words)
        - Required elements present
        - Appropriate terminology
        - Regulatory completeness
        """
        word_count = len(narrative.split())
        requirements = get_regulatory_requirements()
        narrative_lower = narrative.lower()
        required_terms = requirements["terminology"]
        missing_terms = [
            term for term in required_terms if term.lower() not in narrative_lower
        ]
        terminology_tokens = [
            term.lower() for term in required_terms
        ] + ["sar", "threshold", "suspicious"]
        has_required_term = any(token in narrative_lower for token in terminology_tokens)
        has_subject = "customer" in narrative_lower or "subject" in narrative_lower
        has_activity = any(
            token in narrative_lower
            for token in [
                "suspicious",
                "structuring",
                "fraud",
                "sanction",
                "money laundering",
            ]
        )
        has_timeframe = any(
            token in narrative_lower
            for token in ["day", "week", "month", "year", "date", "period"]
        )
        has_amounts = any(char.isdigit() for char in narrative)
        has_indicators = any(
            token in narrative_lower for token in ["threshold", "pattern", "multiple"]
        )
        required_citation_tokens = [
            "31 cfr 1020.320",
            "12 cfr 21.11",
            "fincen sar",
            "31 usc 5324",
        ]
        citations_lower = [citation.lower() for citation in citations]
        has_citations = bool(citations) and any(
            token in citation for citation in citations_lower
            for token in required_citation_tokens
        )
        missing_elements = []
        if not has_subject:
            missing_elements.append("subject")
        if not has_activity:
            missing_elements.append("activity")
        if not has_timeframe:
            missing_elements.append("timeframe")
        if not has_amounts:
            missing_elements.append("amounts")
        if not has_indicators:
            missing_elements.append("indicators")
        if not has_required_term:
            missing_elements.append("terminology")
        if not has_citations:
            missing_elements.append("citations")
        is_complete = not missing_elements
        return {
            "word_count": word_count,
            "within_word_limit": word_count <= requirements["word_limit"],
            "missing_terms": missing_terms,
            "missing_elements": missing_elements,
            "is_complete": is_complete,
        }

    def _format_transactions_for_compliance(
        self, transactions: List[TransactionData]
    ) -> str:
        if not transactions:
            return "No transactions available."
        lines = []
        for idx, txn in enumerate(transactions, start=1):
            amount = f"${txn.amount:,.2f}"
            line = f"{idx}. {txn.transaction_date}: {amount} {txn.transaction_type}"
            if txn.location:
                line += f" at {txn.location}"
            line += f" via {txn.method}"
            lines.append(line)
        return "\n".join(lines)

# ===== REACT PROMPTING HELPERS =====

def create_react_framework():
    """Helper function showing ReACT structure
    
    TODO: Study this example and adapt for compliance narratives:
    
    **REASONING Phase:**
    1. Review the risk analyst's findings
    2. Assess regulatory narrative requirements
    3. Identify key compliance elements
    4. Consider narrative structure
    
    **ACTION Phase:**
    1. Draft concise narrative (≤120 words)
    2. Include specific details and amounts
    3. Reference suspicious activity pattern
    4. Ensure regulatory language
    """
    return {
        "reasoning_phase": [
            "Review risk analysis findings",
            "Assess regulatory requirements", 
            "Identify compliance elements",
            "Plan narrative structure"
        ],
        "action_phase": [
            "Draft concise narrative",
            "Include specific details",
            "Reference activity patterns",
            "Use regulatory language"
        ]
    }

def get_regulatory_requirements():
    """Key regulatory requirements for SAR narratives
    
    TODO: Use these requirements in your prompts:
    """
    return {
        "word_limit": 120,
        "required_elements": [
            "Customer identification",
            "Suspicious activity description", 
            "Transaction amounts and dates",
            "Why activity is suspicious"
        ],
        "terminology": [
            "Suspicious activity",
            "Regulatory threshold",
            "Financial institution",
            "Money laundering",
            "Bank Secrecy Act"
        ],
        "citations": [
            "31 CFR 1020.320 (BSA)",
            "12 CFR 21.11 (SAR Filing)",
            "FinCEN SAR Instructions"
        ]
    }

# ===== TESTING UTILITIES =====

def test_narrative_generation():
    """Test the agent with sample risk analysis
    
    TODO: Use this function to test your implementation:
    - Create sample risk analysis results
    - Initialize compliance agent
    - Generate narrative
    - Validate compliance requirements
    """
    print("🧪 Testing Compliance Officer Agent")
    print("TODO: Implement test case")

def validate_word_count(text: str, max_words: int = 120) -> bool:
    """Helper to validate word count
    
    TODO: Use this utility in your validation:
    """
    word_count = len(text.split())
    return word_count <= max_words

if __name__ == "__main__":
    print("✅ Compliance Officer Agent Module")
    print("ReACT prompting for regulatory narrative generation")
    print("\n📋 TODO Items:")
    print("• Design ReACT system prompt")
    print("• Implement generate_compliance_narrative method")
    print("• Add narrative validation (word count, terminology)")
    print("• Create regulatory citation system")
    print("• Test with sample risk analysis results")
    print("\n💡 Key Concepts:")
    print("• ReACT: Reasoning + Action structured prompting")
    print("• Regulatory Compliance: BSA/AML requirements")
    print("• Narrative Constraints: Word limits and terminology")
    print("• Audit Logging: Complete decision documentation")
