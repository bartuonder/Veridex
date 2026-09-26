from __future__ import annotations

from dataclasses import dataclass

from api.schemas import RiskLevel


@dataclass(frozen=True)
class ClauseCategory:
    name: str
    risk_level: RiskLevel
    question: str
    keywords: tuple[str, ...]


CLAUSE_CATALOG: tuple[ClauseCategory, ...] = (
    ClauseCategory(
        name="Termination For Convenience",
        risk_level=RiskLevel.CRITICAL,
        question='Highlight the parts of this contract related to "Termination For Convenience".',
        keywords=("terminate for convenience", "terminate at any time", "terminate this agreement", "fesih"),
    ),
    ClauseCategory(
        name="Uncapped Liability",
        risk_level=RiskLevel.CRITICAL,
        question='Highlight the parts of this contract related to "Uncapped Liability".',
        keywords=("unlimited liability", "without limitation of liability", "sınırsız sorumluluk"),
    ),
    ClauseCategory(
        name="Cap On Liability",
        risk_level=RiskLevel.HIGH,
        question='Highlight the parts of this contract related to "Cap On Liability".',
        keywords=("limitation of liability", "aggregate liability", "shall not exceed", "sorumluluk sınır"),
    ),
    ClauseCategory(
        name="Liquidated Damages",
        risk_level=RiskLevel.HIGH,
        question='Highlight the parts of this contract related to "Liquidated Damages".',
        keywords=("liquidated damages", "penalty", "cezai şart", "tazminat"),
    ),
    ClauseCategory(
        name="Renewal Term",
        risk_level=RiskLevel.HIGH,
        question='Highlight the parts of this contract related to "Renewal Term".',
        keywords=("automatically renew", "auto-renew", "successive renewal", "otomatik olarak yenilen"),
    ),
    ClauseCategory(
        name="Notice Period To Terminate Renewal",
        risk_level=RiskLevel.MEDIUM,
        question='Highlight the parts of this contract related to "Notice Period To Terminate Renewal".',
        keywords=("written notice", "days prior to", "notice period", "ihbar süresi"),
    ),
    ClauseCategory(
        name="Exclusivity",
        risk_level=RiskLevel.HIGH,
        question='Highlight the parts of this contract related to "Exclusivity".',
        keywords=("exclusive right", "sole and exclusive", "exclusively", "münhasır"),
    ),
    ClauseCategory(
        name="Non-Compete",
        risk_level=RiskLevel.HIGH,
        question='Highlight the parts of this contract related to "Non-Compete".',
        keywords=("shall not compete", "non-competition", "rekabet etmeme"),
    ),
    ClauseCategory(
        name="Change Of Control",
        risk_level=RiskLevel.HIGH,
        question='Highlight the parts of this contract related to "Change Of Control".',
        keywords=("change of control", "merger or acquisition", "kontrol değişikliği"),
    ),
    ClauseCategory(
        name="Anti-Assignment",
        risk_level=RiskLevel.MEDIUM,
        question='Highlight the parts of this contract related to "Anti-Assignment".',
        keywords=("may not assign", "prior written consent to assign", "devredilemez"),
    ),
    ClauseCategory(
        name="Most Favored Nation",
        risk_level=RiskLevel.HIGH,
        question='Highlight the parts of this contract related to "Most Favored Nation".',
        keywords=("most favored", "no less favorable", "en avantajlı"),
    ),
    ClauseCategory(
        name="Minimum Commitment",
        risk_level=RiskLevel.MEDIUM,
        question='Highlight the parts of this contract related to "Minimum Commitment".',
        keywords=("minimum purchase", "minimum commitment", "asgari alım"),
    ),
    ClauseCategory(
        name="IP Ownership Assignment",
        risk_level=RiskLevel.HIGH,
        question='Highlight the parts of this contract related to "IP Ownership Assignment".',
        keywords=("intellectual property shall", "hereby assigns", "work product", "fikri mülkiyet"),
    ),
    ClauseCategory(
        name="Audit Rights",
        risk_level=RiskLevel.MEDIUM,
        question='Highlight the parts of this contract related to "Audit Rights".',
        keywords=("audit", "inspect the records", "denetim hakkı"),
    ),
    ClauseCategory(
        name="Insurance",
        risk_level=RiskLevel.LOW,
        question='Highlight the parts of this contract related to "Insurance".',
        keywords=("insurance", "insurer", "sigorta"),
    ),
    ClauseCategory(
        name="Governing Law",
        risk_level=RiskLevel.LOW,
        question='Highlight the parts of this contract related to "Governing Law".',
        keywords=("governed by the laws", "governing law", "yetkili mahkeme", "uygulanacak hukuk"),
    ),
)

def normalize_category_name(name: str) -> str:
    collapsed = "".join(character.lower() if character.isalnum() else "_" for character in name)
    return "_".join(part for part in collapsed.split("_") if part)


CATALOG_BY_NAME: dict[str, ClauseCategory] = {entry.name: entry for entry in CLAUSE_CATALOG}
CATALOG_BY_NORMALIZED_NAME: dict[str, ClauseCategory] = {
    normalize_category_name(entry.name): entry for entry in CLAUSE_CATALOG
}


def resolve_category(name: str) -> ClauseCategory | None:
    if name in CATALOG_BY_NAME:
        return CATALOG_BY_NAME[name]
    return CATALOG_BY_NORMALIZED_NAME.get(normalize_category_name(name))


def select_categories(requested_names: list[str] | None) -> tuple[ClauseCategory, ...]:
    if not requested_names:
        return CLAUSE_CATALOG
    resolved: list[ClauseCategory] = []
    unknown: list[str] = []
    for name in requested_names:
        category = resolve_category(name)
        if category is None:
            unknown.append(name)
            continue
        resolved.append(category)
    if unknown:
        raise KeyError(f"Unknown clause categories: {unknown}")
    return tuple(resolved)
