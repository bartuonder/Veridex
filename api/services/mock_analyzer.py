from __future__ import annotations

import uuid
from datetime import datetime, timezone

from api.clause_catalog import ClauseCategory, select_categories
from api.schemas import AnalyzeRequest, AnalyzeResponse, ClauseFinding
from api.services.chunking import locate_chunk_index, split_document
from api.services.risk import summarize_risk
from api.settings import Settings

MOCK_MODEL_SOURCE = "mock-analyzer-no-model-loaded"
MOCK_CONFIDENCE = 0.5
SENTENCE_TERMINATORS = ".;\n"
MAX_CLAUSE_CHARACTERS = 600


class MockClauseAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        chunks = split_document(
            request.document_text,
            self.settings.chunk_characters,
            self.settings.chunk_overlap_characters,
        )
        categories = select_categories(request.clause_categories)
        lowered_document = request.document_text.lower()

        findings: list[ClauseFinding] = []
        for category in categories:
            span = self._locate_clause(request.document_text, lowered_document, category)
            if span is None:
                continue
            character_start, character_end = span
            findings.append(
                ClauseFinding(
                    category=category.name,
                    risk_level=category.risk_level,
                    clause_text=request.document_text[character_start:character_end].strip(),
                    character_start=character_start,
                    character_end=character_end,
                    chunk_index=locate_chunk_index(chunks, character_start),
                    confidence=MOCK_CONFIDENCE,
                )
            )

        detected_categories = {finding.category for finding in findings}
        return AnalyzeResponse(
            analysis_id=str(uuid.uuid4()),
            document_name=request.document_name,
            contract_type=request.contract_type,
            analyzed_at=datetime.now(timezone.utc),
            document_characters=len(request.document_text),
            chunk_count=len(chunks),
            model_source=MOCK_MODEL_SOURCE,
            is_mock_response=True,
            findings=findings,
            risk_summary=summarize_risk(findings),
            categories_without_findings=[
                category.name for category in categories if category.name not in detected_categories
            ],
        )

    def _locate_clause(
        self,
        document_text: str,
        lowered_document: str,
        category: ClauseCategory,
    ) -> tuple[int, int] | None:
        earliest_position: int | None = None
        for keyword in category.keywords:
            position = lowered_document.find(keyword.lower())
            if position != -1 and (earliest_position is None or position < earliest_position):
                earliest_position = position
        if earliest_position is None:
            return None
        return expand_to_sentence(document_text, earliest_position)


def expand_to_sentence(document_text: str, position: int) -> tuple[int, int]:
    start = position
    while start > 0 and document_text[start - 1] not in SENTENCE_TERMINATORS:
        start -= 1
    end = position
    while end < len(document_text) and document_text[end] not in SENTENCE_TERMINATORS:
        end += 1
    if end < len(document_text):
        end += 1
    if end - start > MAX_CLAUSE_CHARACTERS:
        end = start + MAX_CLAUSE_CHARACTERS
    return start, end


