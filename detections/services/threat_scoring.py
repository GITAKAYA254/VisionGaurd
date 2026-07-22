"""Central scoring rules for behaviour-based incidents."""
from dataclasses import dataclass


SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class ThreatAssessment:
    risk_score: int
    severity: str


class ThreatScoringService:
    """Keep Sprint 3.1 behaviour scores in one explicit, testable place."""

    SCORES = {
        "LOITERING": 50,
        "RESTRICTED_ZONE": 75,
    }

    @classmethod
    def severity_for_score(cls, score):
        if score <= 30:
            return SEVERITY_LOW
        if score <= 60:
            return SEVERITY_MEDIUM
        if score <= 80:
            return SEVERITY_HIGH
        return SEVERITY_CRITICAL

    @classmethod
    def assess(cls, behaviour_type):
        score = cls.SCORES[behaviour_type]
        return ThreatAssessment(score, cls.severity_for_score(score))
