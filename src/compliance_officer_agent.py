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
import re
import openai
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from pydantic import ValidationError

from src.foundation_sar import (
    ComplianceOfficerOutput,
    ExplainabilityLogger,
    CaseData,
    RiskAnalystOutput,
    TransactionData,
    compliance_officer_output_parse_fallback,
    json_loads_llm_candidate,
)

# Load environment variables
load_dotenv()


def _nar_check_space(text: str) -> str:
    """Lowercase normalization for deterministic substring checks."""
    lowered = text.lower().replace("-", " ")
    return re.sub(r"\s+", " ", lowered).strip()


def _co_narrative_has_time_anchor(case_data: CaseData, narrative: str) -> bool:
    if re.search(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}", narrative):
        return True
    for txn in case_data.transactions:
        if txn.transaction_date and txn.transaction_date in narrative:
            return True
    return False


def _co_citation_echoed_in_narrative(citation: str, narrative_lower: str) -> bool:
    c = citation.strip().lower()
    if not c:
        return False
    nar_chk = _nar_check_space(narrative_lower)
    if c in nar_chk:
        return True
    for inner in (
        m.group(1).strip().lower() for m in re.finditer(r"\(([^)]{2,})\)", citation.strip())
    ):
        if len(inner) >= 3 and inner in nar_chk:
            return True
    for token in re.findall(r"[a-z0-9]{4,}", c):
        if token in nar_chk:
            return True
    for num in re.findall(r"\d{3,}", citation):
        if num in narrative_lower:
            return True
    return False


def _narrative_covers_key_indicator(nar_chk: str, indicator: str) -> bool:
    """Full phrase or a significant token (≥5 chars) from the Risk Analyst key_indicator."""
    ind = indicator.strip().lower()
    if not ind:
        return False
    if ind in nar_chk:
        return True
    compact = nar_chk.replace(" ", "")
    for token in re.findall(r"[a-z0-9]{5,}", ind.replace("-", " ").replace("/", " ")):
        if token in nar_chk or token in compact:
            return True
    return False


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

Machine checks (non-fallback): ≤120 words; mandated phrases from regulatory terminology list;
customer name/id or explicit subject referent; suspicious-activity description with transaction cue;
a case date or YYYY-MM-DD/slash date; dollar/amount cue; at least one Risk Analyst key_indicator echoed;
brief why-it-matters wording; non-empty regulatory_citations each echoed in the narrative.
Set completeness_check true only after these pass (do not rely on the JSON flag alone).
"""

    _COMPLIANCE_JSON_CORRECTION_PROMPT = (
        "Your prior reply was not valid JSON or failed schema validation. Reply with ONLY one raw JSON "
        "(no markdown fences): narrative, narrative_reasoning, regulatory_citations, completeness_check. "
        "Narrative ≤120 words and must pass the system-prompt machine checks (terminology, subject, dates/amounts, "
        "≥1 key_indicator echoed, citations echoed)."
    )

    def _compliance_output_from_message_content(self, content: str) -> Optional[ComplianceOfficerOutput]:
        try:
            json_text = self._extract_json_from_response(content)
        except ValueError:
            return None
        try:
            data = json_loads_llm_candidate(json_text)
            return ComplianceOfficerOutput(**data)
        except (json.JSONDecodeError, ValidationError, TypeError):
            return None

    def generate_compliance_narrative(self, case_data, risk_analysis) -> "ComplianceOfficerOutput":
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
        prompt_base = (
            "Case Context:\n"
            f"Customer: {case_data.customer.name} ({case_data.customer.customer_id})\n"
            f"Risk Rating: {case_data.customer.risk_rating}\n\n"
            "Risk Analysis Summary:\n"
            f"{risk_summary}\n\n"
            "Transactions:\n"
            f"{transaction_summary}\n"
        )
        prompt = prompt_base + compliance_qa_contract_block(case_data, risk_analysis)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=800,
            )
            content_primary = response.choices[0].message.content or ""
            recovery_path = "direct"
            json_recovery: Dict[str, Any] = {"path": recovery_path}
            last_agent_content = (
                json.dumps({"raw_content": content_primary}, ensure_ascii=False)
                if content_primary.strip()
                else "(empty assistant message)"
            )
            result = self._compliance_output_from_message_content(content_primary)

            if result is None:
                retry_resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": content_primary},
                        {"role": "user", "content": self._COMPLIANCE_JSON_CORRECTION_PROMPT},
                    ],
                    temperature=0.1,
                    max_tokens=800,
                )
                content_retry = retry_resp.choices[0].message.content or ""
                last_agent_content = content_retry or last_agent_content
                result = self._compliance_output_from_message_content(content_retry)
                if result is not None:
                    recovery_path = "retry"

            if result is None:
                result = compliance_officer_output_parse_fallback(
                    case_data.case_id, case_data.customer.name
                )
                recovery_path = "fallback"

            if recovery_path == "fallback":
                result = result.model_copy(update={"completeness_check": False})
            else:
                try:
                    result = self._finalize_compliance_output_with_deterministic_qa(
                        case_data,
                        risk_analysis,
                        result,
                    )
                    json_recovery["deterministic_qa"] = "pass"
                except ValueError as qa_exc:
                    repair_user = (
                        "Your prior SAR JSON failed deterministic SAR validation.\n\n"
                        f"{compliance_qa_contract_block(case_data, risk_analysis)}\n"
                        "VALIDATION_ERRORS (verbatim):\n"
                        f"{qa_exc}\n\n"
                        "Fix ALL issues above. Narrative MUST include verbatim (case/format as shown) EVERY phrase "
                        "under 'MANDATORY VERBATIM PHRASES' plus at least ONE actual transaction date/currency cue from Transactions. "
                        "Echo at least one Risk Analyst Key Indicator verbatim or by substantive wording (see list). "
                        "Return ONLY raw JSON matching the schema; no markdown."
                    )
                    repair_resp = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": prompt},
                            {"role": "assistant", "content": last_agent_content},
                            {"role": "user", "content": repair_user},
                        ],
                        temperature=0.05,
                        max_tokens=900,
                    )
                    content_qa_fix = repair_resp.choices[0].message.content or ""
                    repaired = self._compliance_output_from_message_content(content_qa_fix)
                    json_recovery["deterministic_qa_repair_attempted"] = True
                    if repaired is None:
                        json_recovery["deterministic_qa_repair"] = "parse_failed"
                        raise ValueError(str(qa_exc)) from qa_exc
                    result = self._finalize_compliance_output_with_deterministic_qa(
                        case_data,
                        risk_analysis,
                        repaired,
                    )
                    json_recovery["deterministic_qa"] = "pass_after_repair"

            execution_time_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            json_recovery["path"] = recovery_path
            log_payload = dict(result.model_dump())
            log_payload["json_recovery"] = json_recovery
            narrative_reason_log = result.narrative_reasoning
            if recovery_path == "fallback":
                narrative_reason_log = (
                    f"{narrative_reason_log} "
                    "(Degraded fallback after JSON/schema recovery; narrative placeholders parsing_failed wording.)"
                ).strip()

            self.logger.log_agent_action(
                agent_type="ComplianceOfficer",
                action="generate_narrative",
                case_id=case_data.case_id,
                input_data={
                    "case_id": case_data.case_id,
                    "customer_id": case_data.customer.customer_id,
                    "risk_analysis": risk_analysis.model_dump(mode="json"),
                },
                output_data=log_payload,
                reasoning=narrative_reason_log,
                execution_time_ms=execution_time_ms,
                success=True,
                error_message=None,
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
                input_data={
                    "case_id": case_data.case_id,
                    "customer_id": case_data.customer.customer_id,
                    "risk_analysis": risk_analysis.model_dump(mode="json"),
                },
                output_data={},
                reasoning="Compliance narrative generation failed; see error message.",
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

    def _finalize_compliance_output_with_deterministic_qa(
        self,
        case_data: CaseData,
        risk_analysis: RiskAnalystOutput,
        output: ComplianceOfficerOutput,
    ) -> ComplianceOfficerOutput:
        """Minimal deterministic gate: terminology, SAR staples, citations, derived completeness_check."""
        requirements = get_regulatory_requirements()
        narrative = output.narrative
        nar_l = narrative.lower()
        nar_chk = _nar_check_space(narrative)
        failures: List[str] = []

        word_count = len(narrative.split())
        if word_count > requirements["word_limit"]:
            failures.append(
                f"word count {word_count} exceeds {requirements['word_limit']} word SAR cap"
            )

        for term in requirements["terminology"]:
            if _nar_check_space(term) not in nar_chk:
                failures.append(f'missing mandated terminology phrase: "{term}"')

        name_l = case_data.customer.name.strip().lower()
        cid_l = case_data.customer.customer_id.strip().lower()
        name_chk = _nar_check_space(case_data.customer.name)
        subject_ok = (
            (name_l and name_l in nar_l)
            or (name_chk and name_chk in nar_chk)
            or (cid_l and cid_l in nar_l)
        )
        if not subject_ok and not re.search(
            r"\b(customer|subject|account holder|client)\b", nar_l
        ):
            failures.append(
                "subject anchor missing (customer name/id or explicit SAR subject referent)"
            )

        activity_ok = ("suspicious activity" in nar_chk) or (
            ("suspicious" in nar_chk)
            and bool(
                re.search(
                    r"\b(deposit|transaction|transactions|transfer|wire|withdrawal|payment|conduct)\b",
                    nar_chk,
                )
            )
        )
        if not activity_ok:
            failures.append(
                "suspicious-activity characterization with a transaction/action cue is required"
            )

        if not _co_narrative_has_time_anchor(case_data, narrative):
            failures.append(
                "timeframe missing (use a case transaction date or YYYY-MM-DD / MM/DD/YYYY style date)"
            )

        if not (
            "$" in narrative
            or "usd" in nar_l
            or bool(re.search(r"\b\d{3,}(?:,\d{3})*(?:\.\d{2})?\b", narrative))
        ):
            failures.append("monetary amount cue missing ($, USD, or substantive digit amount)")

        ki_list = [k for k in risk_analysis.key_indicators if k and str(k).strip()]
        if not ki_list:
            failures.append("Risk Analyst key_indicators empty — cannot validate indicator coverage")
        elif not any(_narrative_covers_key_indicator(nar_chk, ki) for ki in ki_list):
            failures.append(
                "narrative must echo at least one Risk Analyst key_indicator phrase"
            )

        if not re.search(
            r"\b(because|consistent with|indicative|elevated|concerns?|potential|pattern|"
            r"risk|suggest|raise[ds]?|appear[sd]?)\b",
            nar_chk,
        ):
            failures.append(
                "brief suspicion rationale required (e.g., consistent with / concern / indicative / pattern / risk)"
            )

        cites = [str(c).strip() for c in output.regulatory_citations]
        cites = [c for c in cites if c]
        if not cites:
            failures.append("regulatory_citations must list at least one entry")
        for cite in cites:
            if len(cite) < 8:
                failures.append(f"citation entry too terse for audit review: '{cite}'")
            elif not _co_citation_echoed_in_narrative(cite, nar_l):
                failures.append(f'narrative must echo regulatory citation: "{cite}"')

        if failures:
            joined = "; ".join(failures)
            raise ValueError(f"Compliance narrative failed SAR deterministic validation: {joined}")

        return output.model_copy(update={"completeness_check": True})

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


def compliance_qa_contract_block(
    case_data: CaseData, risk_analysis: RiskAnalystOutput
) -> str:
    """Pinned checklist appended to user prompt so deterministic QA aligns with wording checks."""
    req = get_regulatory_requirements()
    phrases = "\n".join(f'  • "{phrase}"' for phrase in req["terminology"])
    sample_dates = [
        str(t.transaction_date)
        for t in case_data.transactions[:16]
        if getattr(t, "transaction_date", None)
    ]
    uniq_dates = list(dict.fromkeys(sample_dates))
    date_hint = (
        ", ".join(uniq_dates[:6])
        if uniq_dates
        else "use at least one YYYY-MM-DD or MM/DD/YYYY appearing in Transactions"
    )
    ki_block = "\n".join(f"  • {indicator}" for indicator in risk_analysis.key_indicators[:16])
    if not ki_block.strip():
        ki_block = "  • (reuse themes from Classification / Reasoning verbatim where possible)"

    cite_block = "\n".join(
        f'  • regulatory_citations must include verbatim: "{c}" and echo it inside narrative.'
        for c in req["citations"][:5]
    )
    extra_amt = ""
    if case_data.transactions:
        t0 = case_data.transactions[0]
        extra_amt = f"\nSample amount/date format from data: ${t0.amount:,.2f} on {t0.transaction_date}.\n"

    return (
        "\n--- MANDATORY SAR CONTRACT (validated after generation) ---\n"
        "The narrative field MUST simultaneously satisfy ALL of these machine checks:\n"
        f"- Word limit: {req['word_limit']} narrative words maximum.\n"
        "MANDATORY VERBATIM PHRASES (each substring must appear in narrative text):\n"
        f"{phrases}\n"
        "- Include the wording suspicious activity and reference transactions/deposits/transfers/withdrawals "
        "(action cue).\n"
        "- Include timeframe: paste at least one transaction date listed under Transactions "
        "(or equivalent YYYY-MM-DD / MM/DD/YYYY).\n"
        f"- Prefer these case dates where applicable: {date_hint}\n"
        "- Mention the customer full name AND/OR customer identifier OR vocabulary like "
        "customer/subject/account holder/client.\n"
        "- Include $ or substantive digit amount aligning with Transactions.\n"
        "- Brief suspicion rationale wording (patterns like consistent with / concern / indicative / "
        "pattern / risk).\n"
        "ECHO at least one substantive phrase from EACH Risk Analyst key indicator shown below:\n"
        f"{ki_block}\n"
        "CITATIONS (verbatim strings to list and weave into narrative text):\n"
        f"{cite_block}{extra_amt}"
        "--- END CONTRACT ---\n"
    )


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
