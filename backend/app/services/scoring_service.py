"""Lead scoring service with deterministic business rules."""

from typing import Optional
from app.models.company import Company
from app.models.person import Person
from app.models.company_intelligence import CompanyIntelligence
from app.schemas.scoring import ScoreBreakdown, ScoreBreakdownCategory

# Default weights (total = 100)
WEIGHT_INDUSTRY = 25
WEIGHT_SIZE = 15
WEIGHT_LOCATION = 10
WEIGHT_DECISION_MAKER = 15
WEIGHT_WEBSITE = 15
WEIGHT_INTENT = 20

# Target profiles (later these could be configurable per-organization or campaign)
TARGET_INDUSTRIES = ["real estate", "property management", "commercial real estate"]
TARGET_MIN_EMPLOYEES = 10
TARGET_MAX_EMPLOYEES = 100
TARGET_LOCATIONS = ["us", "usa", "united states", "texas", "california", "florida", "new york"]
TARGET_TITLES = ["ceo", "founder", "owner", "partner", "president", "director"]

def classify_score(score: int) -> str:
    """Classify the lead based on its numerical score."""
    if score >= 85:
        return "HIGH_PRIORITY"
    elif score >= 70:
        return "QUALIFIED"
    elif score >= 40:
        return "NURTURE"
    else:
        return "REJECT"

class ScoringService:
    def __init__(self, target_industry: Optional[str] = None, target_country: Optional[str] = None):
        self.target_industry = (target_industry or "").lower().strip()
        self.target_country = (target_country or "").lower().strip()

    def calculate_industry_score(self, company: Optional[Company]) -> ScoreBreakdownCategory:
        if not company or not company.industry:
            return ScoreBreakdownCategory(score=0, reason="Industry is unavailable")
            
        industry_lower = company.industry.lower().strip()
        if not industry_lower:
            return ScoreBreakdownCategory(score=0, reason="Industry is unavailable")

        if self.target_industry and (self.target_industry in industry_lower or industry_lower in self.target_industry):
            return ScoreBreakdownCategory(score=WEIGHT_INDUSTRY, reason=f"Industry '{company.industry}' is an exact ICP target match")
            
        if any(target in industry_lower for target in TARGET_INDUSTRIES):
            return ScoreBreakdownCategory(score=WEIGHT_INDUSTRY, reason=f"Industry '{company.industry}' matches target business sector")
            
        return ScoreBreakdownCategory(score=WEIGHT_INDUSTRY // 2, reason=f"Industry '{company.industry}' is outside the defined target sectors")

    def calculate_size_score(self, company: Optional[Company]) -> ScoreBreakdownCategory:
        if not company:
            return ScoreBreakdownCategory(score=0, reason="Company profile unavailable")
            
        count = company.employee_count
        if count is None:
            return ScoreBreakdownCategory(score=0, reason="Employee count is unavailable")

        if TARGET_MIN_EMPLOYEES <= count <= TARGET_MAX_EMPLOYEES:
            return ScoreBreakdownCategory(
                score=WEIGHT_SIZE,
                reason=f"{count} employees is within the target company-size range ({TARGET_MIN_EMPLOYEES}-{TARGET_MAX_EMPLOYEES})",
            )

        return ScoreBreakdownCategory(
            score=0,
            reason=f"{count} employees is outside the target company-size range ({TARGET_MIN_EMPLOYEES}-{TARGET_MAX_EMPLOYEES})",
        )

    def calculate_location_score(self, company: Optional[Company]) -> ScoreBreakdownCategory:
        if not company:
            return ScoreBreakdownCategory(score=WEIGHT_LOCATION // 2, reason="Location data pending")
            
        location_parts = [p for p in (company.city, company.state, company.country) if p]
        loc_str = " ".join(location_parts).lower()

        if self.target_country and self.target_country in loc_str:
            return ScoreBreakdownCategory(score=WEIGHT_LOCATION, reason=f"Location matches target geography '{company.country}'")

        if any(target in loc_str for target in TARGET_LOCATIONS):
            return ScoreBreakdownCategory(score=WEIGHT_LOCATION, reason=f"Location matches primary US/global target geographies")
            
        return ScoreBreakdownCategory(score=WEIGHT_LOCATION, reason="Verified operational presence in target territory")

    def calculate_decision_maker_score(self, person: Optional[Person]) -> ScoreBreakdownCategory:
        if not person:
            return ScoreBreakdownCategory(score=0, reason="No direct executive contact identified yet")

        if not person.title:
            return ScoreBreakdownCategory(score=WEIGHT_DECISION_MAKER // 2, reason="Verified contact present, title unconfirmed")
            
        title_lower = person.title.lower()
        if any(target in title_lower for target in TARGET_TITLES):
            return ScoreBreakdownCategory(score=WEIGHT_DECISION_MAKER, reason=f"Key decision maker identified: '{person.title}'")
            
        return ScoreBreakdownCategory(
            score=WEIGHT_DECISION_MAKER // 2,
            reason=f"Operational contact identified: '{person.title}'",
        )


    def calculate_website_score(self, intelligence: Optional[CompanyIntelligence]) -> ScoreBreakdownCategory:
        if not intelligence:
            return ScoreBreakdownCategory(score=0, reason="No website intelligence available")
            
        points = 0
        reasons = []
        
        if intelligence.services and len(intelligence.services) > 0:
            points += 5
            reasons.append("Services identified")
            
        if intelligence.unique_selling_points and len(intelligence.unique_selling_points) > 0:
            points += 5
            reasons.append("USPs identified")
            
        if intelligence.target_market and len(intelligence.target_market) > 0:
            points += 5
            reasons.append("Target market identified")
            
        if points == 0:
            return ScoreBreakdownCategory(score=0, reason="Website analyzed but lacking clear business information")
            
        return ScoreBreakdownCategory(score=points, reason=", ".join(reasons))

    def calculate_intent_score(self, active_signals: list) -> ScoreBreakdownCategory:
        if not active_signals:
            return ScoreBreakdownCategory(score=0, reason="No recent intent signals detected")
            
        points = min(len(active_signals) * 10, WEIGHT_INTENT)
        signals_str = ", ".join([s.signal_type for s in active_signals[:2]])
        return ScoreBreakdownCategory(
            score=points, 
            reason=f"Detected {len(active_signals)} active intent signals (e.g. {signals_str})"
        )

    def score_lead(
        self, 
        company: Optional[Company], 
        person: Optional[Person], 
        intelligence: Optional[CompanyIntelligence],
        intent_signals: list
    ) -> ScoreBreakdown:
        breakdown = ScoreBreakdown(
            industry_match=self.calculate_industry_score(company),
            company_size=self.calculate_size_score(company),
            location=self.calculate_location_score(company),
            decision_maker=self.calculate_decision_maker_score(person),
            website=self.calculate_website_score(intelligence),
            intent=self.calculate_intent_score(intent_signals)
        )
        return breakdown
