from __future__ import annotations

import uuid
from datetime import datetime, timezone

import torch

from api.clause_catalog import ClauseCategory, select_categories
from api.schemas import AnalyzeRequest, AnalyzeResponse, ClauseFinding
from api.services.model_loader import LoadedModel, load_model
from api.services.risk import summarize_risk
from api.settings import Settings

CONTEXT_SEQUENCE_ID = 1
CLS_TOKEN_INDEX = 0


class ModelClauseAnalyzer:
    def __init__(self, settings: Settings, loaded_model: LoadedModel | None = None) -> None:
        self.settings = settings
        self.loaded_model = loaded_model or load_model(settings)

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        categories = select_categories(request.clause_categories)
        findings: list[ClauseFinding] = []
        window_count = 0

        for category in categories:
            extraction = self._extract_clause(request.document_text, category)
            window_count = max(window_count, extraction["window_count"])
            if extraction["clause_text"] is None:
                continue
            findings.append(
                ClauseFinding(
                    category=category.name,
                    risk_level=category.risk_level,
                    clause_text=extraction["clause_text"].strip(),
                    character_start=extraction["character_start"],
                    character_end=extraction["character_end"],
                    chunk_index=extraction["window_index"],
                    confidence=extraction["confidence"],
                )
            )

        detected_categories = {finding.category for finding in findings}
        return AnalyzeResponse(
            analysis_id=str(uuid.uuid4()),
            document_name=request.document_name,
            contract_type=request.contract_type,
            analyzed_at=datetime.now(timezone.utc),
            document_characters=len(request.document_text),
            chunk_count=window_count,
            model_source=self.loaded_model.source_description,
            is_mock_response=False,
            findings=findings,
            risk_summary=summarize_risk(findings),
            categories_without_findings=[
                category.name for category in categories if category.name not in detected_categories
            ],
        )

    def _extract_clause(self, document_text: str, category: ClauseCategory) -> dict:
        tokenizer = self.loaded_model.tokenizer
        encoded = tokenizer(
            category.question,
            document_text,
            truncation="only_second",
            max_length=self.settings.max_seq_length,
            stride=self.settings.doc_stride,
            return_overflowing_tokens=True,
            return_offsets_mapping=True,
            padding="max_length",
            return_tensors="pt",
        )
        window_count = encoded["input_ids"].shape[0]
        sequence_ids_per_window = [encoded.sequence_ids(index) for index in range(window_count)]
        offset_mapping = encoded.pop("offset_mapping")
        encoded.pop("overflow_to_sample_mapping")

        best_score = -float("inf")
        best_window = 0
        best_character_span = (0, 0)
        best_confidence = 0.0
        minimum_null_score = float("inf")

        for batch_start in range(0, window_count, self.settings.inference_batch_size):
            batch_slice = slice(batch_start, batch_start + self.settings.inference_batch_size)
            batch = {
                key: value[batch_slice].to(self.loaded_model.device) for key, value in encoded.items()
            }
            with torch.no_grad():
                outputs = self.loaded_model.model(**batch)
            start_logits = outputs.start_logits.float().cpu()
            end_logits = outputs.end_logits.float().cpu()

            for offset_in_batch in range(start_logits.shape[0]):
                window_index = batch_start + offset_in_batch
                window_start_logits = start_logits[offset_in_batch]
                window_end_logits = end_logits[offset_in_batch]

                minimum_null_score = min(
                    minimum_null_score,
                    float(window_start_logits[CLS_TOKEN_INDEX] + window_end_logits[CLS_TOKEN_INDEX]),
                )

                candidate = self._best_span_in_window(
                    window_start_logits,
                    window_end_logits,
                    sequence_ids_per_window[window_index],
                )
                if candidate is None or candidate[0] <= best_score:
                    continue
                score, start_index, end_index, confidence = candidate
                best_score = score
                best_window = window_index
                best_confidence = confidence
                best_character_span = (
                    int(offset_mapping[window_index][start_index][0]),
                    int(offset_mapping[window_index][end_index][1]),
                )

        if best_score == -float("inf"):
            return {"clause_text": None, "window_count": window_count}

        score_difference = minimum_null_score - best_score
        if score_difference > self.settings.null_score_diff_threshold:
            return {"clause_text": None, "window_count": window_count}

        return {
            "clause_text": document_text[best_character_span[0] : best_character_span[1]],
            "character_start": best_character_span[0],
            "character_end": best_character_span[1],
            "window_index": best_window,
            "window_count": window_count,
            "confidence": best_confidence,
        }

    def _best_span_in_window(
        self,
        start_logits: torch.Tensor,
        end_logits: torch.Tensor,
        sequence_ids: list[int | None],
    ) -> tuple[float, int, int, float] | None:
        context_positions = [
            position
            for position, sequence_id in enumerate(sequence_ids)
            if sequence_id == CONTEXT_SEQUENCE_ID
        ]
        if not context_positions:
            return None

        start_probabilities = torch.softmax(start_logits, dim=-1)
        end_probabilities = torch.softmax(end_logits, dim=-1)

        top_starts = self._top_positions(start_logits, context_positions)
        top_ends = self._top_positions(end_logits, context_positions)

        best: tuple[float, int, int, float] | None = None
        for start_index in top_starts:
            for end_index in top_ends:
                if end_index < start_index:
                    continue
                if end_index - start_index + 1 > self.settings.max_answer_length:
                    continue
                score = float(start_logits[start_index] + end_logits[end_index])
                if best is None or score > best[0]:
                    confidence = float(
                        start_probabilities[start_index] * end_probabilities[end_index]
                    )
                    best = (score, start_index, end_index, confidence)
        return best

    def _top_positions(self, logits: torch.Tensor, context_positions: list[int]) -> list[int]:
        scored = sorted(
            ((float(logits[position]), position) for position in context_positions), reverse=True
        )
        return [position for _, position in scored[: self.settings.n_best_size]]
