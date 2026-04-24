## LinkedIn Post Prompt (Fintech Theory → Practical Build)

You are writing a LinkedIn post for a senior blockchain/backend engineer who just finished a theory-heavy FinTech course from IIM Calcutta and then built a practical Agentic AI project. Keep the tone natural, human, and concise (no hype, no “AI buzzword soup”). Match a grounded, builder voice.

### Post requirements
- 150–220 words.
- 1–2 short paragraphs + a compact bullet list (3–5 bullets).
- Include the GitHub repo link: https://github.com/Tarunshrma/agentic-ai-financial-compliance-sar
- Mention the course–project bridge: theory → hands-on build like audit logs, multi agent, human in loop and Auditablity in Finance.
- Close with a short forward-looking line (what I want to explore next).
- Optional: 4–6 relevant hashtags (only if it feels natural).

### Theory anchors (from FinTech course – Module 13)
Use these ideas to show conceptual grounding:
- Automated decision engines scale risk assessment and advice.
- Explainability, governance, and accountability are critical in finance.
- Transparency and incentives matter in AI-driven platforms.
- Algorithms can amplify systemic risks if not monitored.

### What I built (project summary)
Agentic AI system for financial compliance (SAR processing):
- Data modeling with Pydantic schemas (Customer, Account, Transaction, Case).
- Multi‑agent workflow: Risk Analyst (Chain‑of‑Thought) → Human gate → Compliance Officer (ReACT).
- Audit trail logger for explainability.
- Two‑stage processing to reduce cost and improve review focus.
- SAR document generation + workflow metrics.

### Why it matters in FinTech
Tie this to:
- AML/SAR compliance and regulatory readiness.
- Faster triage with human oversight.
- Explainable AI decisions for auditors and regulators.

### How to run (mention briefly)
Include a short “run it” snippet in the post or a brief sentence:
- `pip install -r requirements.txt`
- `cp .env.template .env` (add Vocareum key)
- Run `notebooks/03_workflow_integration.ipynb`

### Style guide
- No “as an AI” phrasing.
- No exaggerated claims (“revolutionary”, “game‑changing”).
- Keep sentences short and concrete.
- Use first person (“I built…”, “I learned…”).
