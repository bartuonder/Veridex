from __future__ import annotations

from api.schemas import ClauseFinding, RiskLevel, RiskSummary

RISK_LEVEL_SEVERITY_ORDER = (RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW)


def summarize_risk(findings: list[ClauseFinding]) -> RiskSummary:
    counts = {level: 0 for level in RiskLevel}
    for finding in findings:
        counts[finding.risk_level] += 1
    highest_risk_level = next(
        (level for level in RISK_LEVEL_SEVERITY_ORDER if counts[level] > 0), None
    )
    return RiskSummary(
        critical=counts[RiskLevel.CRITICAL],
        high=counts[RiskLevel.HIGH],
        medium=counts[RiskLevel.MEDIUM],
        low=counts[RiskLevel.LOW],
        highest_risk_level=highest_risk_level,
    )
