"""Pydantic request and response models for the GrihaValue API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.config import (
    AREA_MAX_SQFT,
    AREA_MIN_SQFT_PER_BHK,
    INTEREST_RATE_DEFAULT_PCT,
    INTEREST_RATE_MAX_PCT,
    INTEREST_RATE_MIN_PCT,
    TENURE_DEFAULT_YRS,
    TENURE_MAX_YRS,
    TENURE_MIN_YRS,
)


class EstimateRequest(BaseModel):
    model_config = {"str_strip_whitespace": True, "extra": "forbid"}

    city: str = Field(..., min_length=2, max_length=60)
    locality: str = Field(..., min_length=2, max_length=80)
    bhk: int = Field(..., ge=1, le=5)
    area_sqft: float = Field(..., gt=0, le=AREA_MAX_SQFT)
    bathrooms: int = Field(..., ge=1, le=10)
    property_type: Literal["Apartment", "Builder Floor", "Independent Villa", "Penthouse"]
    furnishing: Literal["Unfurnished", "Semi-Furnished", "Fully Furnished"]
    construction_status: Literal["Ready to Move", "Under Construction"]
    age_years: int = Field(..., ge=0, le=50)
    parking: int = Field(..., ge=0, le=5)
    down_payment_pct: float = Field(default=20.0, ge=0.0, le=100.0)
    annual_rate_pct: float = Field(
        default=INTEREST_RATE_DEFAULT_PCT,
        ge=INTEREST_RATE_MIN_PCT,
        le=INTEREST_RATE_MAX_PCT,
    )
    tenure_years: int = Field(
        default=TENURE_DEFAULT_YRS, ge=TENURE_MIN_YRS, le=TENURE_MAX_YRS,
    )

    @model_validator(mode="after")
    def check_plausibility(self) -> "EstimateRequest":
        if self.area_sqft < self.bhk * AREA_MIN_SQFT_PER_BHK:
            raise ValueError(
                f"area_sqft {self.area_sqft:g} is implausibly small for {self.bhk} BHK "
                f"(minimum {self.bhk * AREA_MIN_SQFT_PER_BHK})"
            )
        if self.bathrooms > self.bhk + 2:
            raise ValueError(f"{self.bathrooms} bathrooms is implausible for {self.bhk} BHK")
        if self.property_type == "Penthouse" and self.bhk < 2:
            raise ValueError("A penthouse must have at least 2 BHK")
        return self


class PriceRange(BaseModel):
    low: float
    high: float
    low_q: float
    high_q: float


class Comparable(BaseModel):
    City: str
    Locality: str
    BHK: int
    Area_SqFt: float
    Price_INR: float
    Price_per_sqft: float
    Construction_Status: str
    Property_Type: str


class EstimateResponse(BaseModel):
    predicted_price: float
    rate_per_sqft: float
    price_range: PriceRange
    city_median_rate_per_sqft: float
    vs_city_median_pct: float
    state: str
    finance: dict
    comparables: list[Comparable]
    comparables_kind: str
    data_provenance: str
    model_name: str
    valuation_ref: str | None = None
    forecast: dict | None = None
    macro_news: list[dict] | None = None


class SensitivityRequest(BaseModel):
    property_value: float = Field(..., gt=0, le=1_000_000_000)
    down_payment_pct: float = Field(default=20.0, ge=0.0, le=100.0)
    rates_pct: list[float] = Field(..., min_length=1, max_length=12)
    tenures_years: list[int] = Field(..., min_length=1, max_length=12)

    @field_validator("rates_pct")
    @classmethod
    def rates_in_bounds(cls, v: list[float]) -> list[float]:
        for r in v:
            if not INTEREST_RATE_MIN_PCT <= r <= INTEREST_RATE_MAX_PCT:
                raise ValueError(f"rate {r} outside {INTEREST_RATE_MIN_PCT}-{INTEREST_RATE_MAX_PCT}")
        return v

    @field_validator("tenures_years")
    @classmethod
    def tenures_in_bounds(cls, v: list[int]) -> list[int]:
        for t in v:
            if not TENURE_MIN_YRS <= t <= TENURE_MAX_YRS:
                raise ValueError(f"tenure {t} outside {TENURE_MIN_YRS}-{TENURE_MAX_YRS}")
        return v


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=20)
    estimate_context: dict = Field(...)


class ContactRequest(BaseModel):
    model_config = {"str_strip_whitespace": True}

    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=120)
    phone: str = Field(..., min_length=7, max_length=25)
    advisory_type: str = Field(default="Full Acquisition Report & Valuation Audit", max_length=100)
    preferred_contact: Literal["phone", "email", "whatsapp"] = "whatsapp"
    notes: str = Field(default="", max_length=2000)
    estimate_context: dict | None = None

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) < 7:
            raise ValueError("Phone number must contain at least 7 digits")
        return v.strip()


class ContactResponse(BaseModel):
    status: Literal["received", "confirmed"]
    lead_id: str
    timestamp: str
    client_name: str
    client_email: str
    advisory_type: str
    report_ready: bool
    summary: dict | None = None
    message: str
