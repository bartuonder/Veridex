from __future__ import annotations

from dataclasses import dataclass

from api.schemas import ModelStatus
from api.services.mock_analyzer import MockClauseAnalyzer
from api.services.model_analyzer import ModelClauseAnalyzer
from api.settings import Settings


@dataclass
class AnalyzerState:
    analyzer: MockClauseAnalyzer | ModelClauseAnalyzer
    model_status: ModelStatus
    model_source: str
    load_error: str | None


_state: AnalyzerState | None = None


def initialise_analyzer(settings: Settings) -> AnalyzerState:
    global _state
    if settings.model_source == "mock":
        _state = AnalyzerState(
            analyzer=MockClauseAnalyzer(settings),
            model_status=ModelStatus.NOT_LOADED,
            model_source="mock",
            load_error=None,
        )
        return _state

    try:
        analyzer = ModelClauseAnalyzer(settings)
    except Exception as error:
        _state = AnalyzerState(
            analyzer=MockClauseAnalyzer(settings),
            model_status=ModelStatus.NOT_LOADED,
            model_source="mock",
            load_error=f"{type(error).__name__}: {error}",
        )
        return _state

    _state = AnalyzerState(
        analyzer=analyzer,
        model_status=ModelStatus.LOADED,
        model_source=analyzer.loaded_model.source_description,
        load_error=None,
    )
    return _state


def get_analyzer_state(settings: Settings) -> AnalyzerState:
    if _state is None:
        return initialise_analyzer(settings)
    return _state


def peek_analyzer_state() -> AnalyzerState | None:
    return _state
