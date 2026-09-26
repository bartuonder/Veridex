from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContractType(str, Enum):
    LEASE = "lease"
    SUPPLY = "supply"
    NDA = "nda"
    SERVICE = "service"
    EMPLOYMENT = "employment"
    OTHER = "other"


class ModelStatus(str, Enum):
    NOT_LOADED = "not_loaded"
    LOADED = "loaded"


class AnalyzeRequest(BaseModel):
    document_name: str = Field(min_length=1, max_length=255)
    document_text: str = Field(min_length=1)
    contract_type: ContractType = ContractType.OTHER
    clause_categories: list[str] | None = Field(default=None, min_length=1)

    @field_validator("document_text")
    @classmethod
    def reject_blank_document(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("document_text must contain non-whitespace characters")
        return value


class ClauseFinding(BaseModel):
    category: str
    risk_level: RiskLevel
    clause_text: str
    character_start: int = Field(ge=0)
    character_end: int = Field(ge=0)
    chunk_index: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)


class RiskSummary(BaseModel):
    critical: int = Field(default=0, ge=0)
    high: int = Field(default=0, ge=0)
    medium: int = Field(default=0, ge=0)
    low: int = Field(default=0, ge=0)
    highest_risk_level: RiskLevel | None = None


class AnalyzeResponse(BaseModel):
    analysis_id: str
    document_name: str
    contract_type: ContractType
    analyzed_at: datetime
    document_characters: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    model_source: str
    is_mock_response: bool
    findings: list[ClauseFinding]
    risk_summary: RiskSummary
    categories_without_findings: list[str]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app_name: str
    app_version: str
    model_status: ModelStatus
    registered_model_name: str
    model_alias: str
    uptime_seconds: float = Field(ge=0.0)


class ErrorResponse(BaseModel):
    detail: str
