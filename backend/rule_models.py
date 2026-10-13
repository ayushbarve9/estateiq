"""SQLAlchemy ORM models for versioned, effective-dated financial rules and valuations.

Every financial constant carries:
- source_title & source_url
- citation_ref (e.g. circular number, gazette notification)
- effective_from & effective_to (point-in-time applicability)
- verified_by & verification_status
"""

from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class LTVRule(Base):
    """RBI Loan-to-Value cap tier, effective-dated with official circular references."""
    __tablename__ = "ltv_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tier_name: Mapped[str] = mapped_column(String(64), nullable=False)
    max_loan_inr: Mapped[float] = mapped_column(Float, nullable=False)  # float("inf") represented as 999999999.0 or similar
    ltv_ratio: Mapped[float] = mapped_column(Float, nullable=False)     # e.g. 0.90, 0.80, 0.75

    citation_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    source_title: Mapped[str] = mapped_column(String(256), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    effective_from: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    verified_by: Mapped[str] = mapped_column(String(128), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), default="VERIFIED", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )


class StampDutyRule(Base):
    """State-level stamp duty and registration rate, effective-dated with gazette references."""
    __tablename__ = "stamp_duty_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    buyer_category: Mapped[str] = mapped_column(String(32), default="General", nullable=False)  # General, Female, Joint
    rate_pct: Mapped[float] = mapped_column(Float, nullable=False)  # e.g. 0.065 for 6.5%

    gazette_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    source_title: Mapped[str] = mapped_column(String(256), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    effective_from: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    verified_by: Mapped[str] = mapped_column(String(128), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), default="APPROXIMATE", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )


class GSTRule(Base):
    """GST rates on residential real estate, effective-dated with GST Council notifications."""
    __tablename__ = "gst_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    construction_status: Mapped[str] = mapped_column(String(64), nullable=False)  # Under Construction, Ready to Move
    is_affordable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    affordable_threshold_inr: Mapped[float] = mapped_column(Float, default=4500000.0, nullable=False)
    rate_pct: Mapped[float] = mapped_column(Float, nullable=False)  # e.g. 0.05, 0.01, 0.0

    notification_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    source_title: Mapped[str] = mapped_column(String(256), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    effective_from: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    verified_by: Mapped[str] = mapped_column(String(128), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), default="VERIFIED", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )


class BenchmarkRateRule(Base):
    """Home loan benchmark floating rates & tenure limits, effective-dated with source citations."""
    __tablename__ = "benchmark_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rate_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # default_rate, min_rate, max_rate, default_tenure, min_tenure, max_tenure
    rate_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(16), default="percentage", nullable=False)  # percentage or years

    citation_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    source_title: Mapped[str] = mapped_column(String(256), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    effective_from: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    verified_by: Mapped[str] = mapped_column(String(128), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )


class ValuationHistory(Base):
    """Persistent valuation record storing calculation and applied rules snapshot."""
    __tablename__ = "valuation_history"

    ref_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    locality: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    bhk: Mapped[int] = mapped_column(Integer, nullable=False)
    area_sqft: Mapped[float] = mapped_column(Float, nullable=False)
    property_type: Mapped[str] = mapped_column(String(64), nullable=False)
    construction_status: Mapped[str] = mapped_column(String(64), nullable=False)
    age_years: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_price: Mapped[float] = mapped_column(Float, nullable=False)
    rate_per_sqft: Mapped[float] = mapped_column(Float, nullable=False)
    p10_price: Mapped[float] = mapped_column(Float, nullable=False)
    p90_price: Mapped[float] = mapped_column(Float, nullable=False)
    vs_city_median_pct: Mapped[float] = mapped_column(Float, nullable=False)
    loan_amount: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_emi: Mapped[float] = mapped_column(Float, nullable=False)
    down_payment: Mapped[float] = mapped_column(Float, nullable=False)
    stamp_duty: Mapped[float] = mapped_column(Float, nullable=False)
    gst: Mapped[float] = mapped_column(Float, nullable=False)
    upfront_cash: Mapped[float] = mapped_column(Float, nullable=False)
    total_acquisition_cost: Mapped[float] = mapped_column(Float, nullable=False)
    forecast_3y: Mapped[float] = mapped_column(Float, nullable=False)
    forecast_5y: Mapped[float] = mapped_column(Float, nullable=False)
    forecast_10y: Mapped[float] = mapped_column(Float, nullable=False)
    cagr_baseline: Mapped[float] = mapped_column(Float, nullable=False)
    raw_payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class LeadDossier(Base):
    """Client consultation and lead advisory dossier."""
    __tablename__ = "leads_dossiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    ref_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("valuation_history.ref_id"), nullable=True)
    client_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[str] = mapped_column(String(64), nullable=False)
    advisory_type: Mapped[str] = mapped_column(String(64), nullable=False)
    preferred_contact: Mapped[str] = mapped_column(String(64), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
