import json
from dotenv import load_dotenv
load_dotenv()

class LeadScorer:

    def __init__(self, llm_client):
        self.llm = llm_client

    # ── LLM dimensions (single call) ──────────────────────────

    def score_llm_dimensions(self, row: dict) -> dict:
        prompt = f"""
You are a B2B lead scoring assistant. Score this lead on 3 dimensions.

--- JOB INFO ---
Title: {row.get('jobTitle', '')}
Description: {str(row.get('jobDescription', ''))[:1500]}

--- COMPANY INFO ---
Industry: {row.get('sector', '')}
Employees: {row.get('companyEmployeeCount', '')}
Funding Stage: {row.get('latest_funding_stage', '')}
Last Funding Date: {row.get('latest_funding_round_date', '')}
Company Description : {row.get('companyDescription')}

--- SIGNALS ---
Review Summary: {str(row.get('Reviews', ''))[:800]}

--- SCORING RULES ---
Read the company desription,If the Company Description suggests that the company is either any of this 3 types 
mentioned below then score D1, D3, D5 as 0:
1. staffing, recruiting, HR, or outsourcing company,  
2. consulting, services, solutions, or agency firmCompany is a marketplace or platform connecting freelancers
3. Company is a marketplace or platform connecting freelancers


Otherwise:
D1 - Execution Signal (0-3):
3 = Customer Support, Technical Support, QA, Implementation, Operations Associate
2 = Similar support/operations role
1 = Borderline role
0 = Strategic, Leadership, Engineering, Developer, Architect

D3 - Company Fit (0-2):
2 = Strong Fit  (SaaS/Tech/E-commerce, 50-300 employees, Series A/B)
1 = Moderate Fit
0 = Poor Fit

D5 - Buying Trigger (0-3):
3 = Strong Trigger  (funding < 12 months, understaffed, burnout, scaling pressure)
2 = Moderate Trigger
1 = Weak Trigger
0 = No Trigger

Reason: (Summery About Scores why it is given)

Return ONLY a valid JSON object, no explanation:
{{"D1": <int>, "D3": <int>, "D5": <int>, "Reason":<string>}}
"""
        response = self.llm(prompt)
        try:
            clean = str(response).strip()
            # Strip markdown fences if present
            clean = clean.replace("```json", "").replace("```", "").strip()
            scores = json.loads(clean)
            return {
                "D1": max(0, min(int(scores["D1"]), 3)),
                "D3": max(0, min(int(scores["D3"]), 2)),
                "D5": max(0, min(int(scores["D5"]), 3)),
                "Reason": scores["Reason"]
            }
        except Exception:
            return {"D1": 0, "D3": 0, "D5": 0,"Reason":"None"}

    # ── Rule-based dimensions ─────────────────────────────────

    def score_hiring_intent(self, row: dict) -> int:
        try:
            repeatability = int(row.get("Repeatability", 0) or 0)
        except (ValueError, TypeError):
            return 0
        if repeatability >= 3:
            return 3
        if repeatability == 2:
            return 2
        if repeatability == 1:
            return 1
        return 0

    def score_remote_readiness(self, row: dict) -> int:
        work_type = str(row.get("workType", "")).lower()
        if "remote" in work_type:
            return 2
        if "hybrid" in work_type:
            return 1
        return 0

    def score_repost_bonus(self, d2: int) -> int:
        return max(0, d2 - 1)

    def score_enrichment_confidence(self, row: dict) -> int:
        signals = [
            bool(row.get("latest_funding_stage")),
            bool(row.get("Reviews") and row.get("Reviews") != "NOT_FOUND"),
            bool(row.get("companyEmployeeCount")),
        ]
        count = sum(signals)
        if count == 3:
            return 2
        if count == 2:
            return 1
        return 0

    # ── Final scoring ─────────────────────────────────────────

    def score_lead(self, row: dict) -> dict:
        llm_scores = self.score_llm_dimensions(row)

        d1 = llm_scores["D1"]
        d2 = self.score_hiring_intent(row)
        d3 = llm_scores["D3"]
        d4 = self.score_remote_readiness(row)
        d5 = llm_scores["D5"]
        d6 = self.score_repost_bonus(d2)
        d7 = self.score_enrichment_confidence(row)
        reason = llm_scores["Reason"]

        # scores = {
        #     "Execution Signal": d1,
        #     "Hiring Intent": d2,
        #     "Company Fit": d3,
        #     "Buying Trigger": d5
        # }
        # zero_reasons = [name for name, value in scores.items() if value == 0]

        # if zero_reasons:
        #     d1 = d2 = d3 = d4 = d5 = d6 = d7 = 0
        #     reason = f"{', '.join(zero_reasons)} is 0, so all scores are 0 and lead is rejected."
        if d2 == 0:
            reason = "As Hiring Intent is 0, everything is 0"

        if 0 in (d1, d2, d3, d5):
            d1 = d2 = d3 = d4 = d5 = d6 = d7 = 0

        total = d1 + d2 + d3 + d4 + d5 + d6 + d7
        decision, priority = self.get_decision(total)

        return {
            "Execution Signal":       d1,
            "Hiring Intent":          d2,
            "Company Fit":            d3,
            "Remote Readiness":       d4,
            "Buying Trigger":         d5,
            "Repost Bonus":           d6,
            "Enrichment Confidence":  d7,
            "total_score":            total,
            "decision":               decision,
            "priority":               priority,
            "reason":                 reason
        }

    # ── Decision logic ────────────────────────────────────────

    @staticmethod
    def get_decision(score: int) -> tuple[str, str]:
        if score >= 13:
            return "KEEP", "HIGH"
        if score >= 9:
            return "KEEP", "MEDIUM"
        if score >= 6:
            return "HOLD", "MONITOR"
        return "REJECT", "-"