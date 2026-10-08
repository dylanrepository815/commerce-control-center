import re
from datetime import datetime
from typing import Literal
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

CheckStatus = Literal["CLEAR", "RISK", "UNKNOWN"]


class EvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    provider: str = Field(min_length=1, max_length=100)
    check_type: Literal["history", "backlinks", "safety", "scamadviser", "niche_fit"]
    source_reference: str = Field(min_length=1, max_length=2000)
    observed_at: datetime
    findings: str = Field(min_length=1, max_length=10000)
    verified: bool = False
    categories: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("observed_at")
    @classmethod
    def aware(cls, v):
        if v.tzinfo is None:
            raise ValueError("Evidence timestamp must include timezone")
        return v


class CandidateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    domain: str = Field(min_length=3, max_length=253)
    source: str = Field(min_length=1, max_length=200)
    acquisition_url: HttpUrl | None = None
    acquisition_price: float | None = Field(default=None, ge=0, le=9999999999)
    currency: str | None = Field(default=None, pattern="^[A-Z]{3}$")
    scamadviser_score: int | None = Field(default=None, ge=0, le=100)
    history_status: CheckStatus = "UNKNOWN"
    backlink_status: CheckStatus = "UNKNOWN"
    safety_status: CheckStatus = "UNKNOWN"
    niche_fit_score: int | None = Field(default=None, ge=0, le=100)
    warnings: list[str] = Field(default_factory=list, max_length=30)
    evidence: list[EvidenceInput] = Field(default_factory=list, max_length=100)

    @field_validator("domain")
    @classmethod
    def valid_domain(cls, value):
        value = value.lower().rstrip(".")
        if not re.fullmatch(
            r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", value
        ):
            raise ValueError("Expected a domain name without path, port or scheme")
        return value

    @model_validator(mode="after")
    def priced(self):
        if self.acquisition_price is not None and self.currency is None:
            raise ValueError("Price needs currency")
        return self


class ResearchSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[CandidateInput] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique(self):
        names = [c.domain for c in self.candidates]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate domain in research run")
        return self
