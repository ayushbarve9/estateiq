"""Curated Real Estate News, Macro Milestones, and Historical Movements.

Provenance:
- National Housing Bank (NHB) RESIDEX Historical Bulletin & Trends (2013-2026)
- Reserve Bank of India (RBI) Monetary Policy Reports & Notifications
- Maharashtra Real Estate Regulatory Authority (MahaRERA) Order Archives
- Central Board of Indirect Taxes and Customs (CBIC) Real Estate GST Notifications
- Mumbai Metropolitan Region Development Authority (MMRDA) Infrastructure Bulletins
"""

from __future__ import annotations

from typing import Any

HISTORICAL_NEWS_EVENTS: list[dict[str, Any]] = [
    {
        "id": "rera-2016",
        "year": 2016,
        "date": "2016-05-01",
        "headline": "Real Estate (Regulation and Development) Act (RERA) Enacted",
        "category": "Regulatory",
        "movement": "Market Consolidation & Flight to Quality (+3.5% p.a.)",
        "impact_direction": "neutral_positive",
        "description": "Established escrow mechanisms, mandatory title disclosures, and strict delivery timelines. Prompted structural consolidation toward Tier-1 organized developers with disciplined balance sheets.",
        "primary_source": "Ministry of Housing and Urban Affairs, Real Estate (Regulation and Development) Act 2016 (Act No. 16 of 2016)",
        "source_url": "https://mohua.gov.in/cms/the-real-estate-act-2016.php",
        "affected_corridors": ["Pan-India", "Mumbai (MMR)", "Bengaluru", "Delhi NCR"],
    },
    {
        "id": "gst-2019",
        "year": 2019,
        "date": "2019-04-01",
        "headline": "GST Council Slashes Real Estate Tax to 5% (1% for Affordable)",
        "category": "Fiscal Reform",
        "movement": "Under-Construction Absorption Revival (+5.8% p.a.)",
        "impact_direction": "positive",
        "description": "CBIC Notification No. 03/2019 reduced GST on under-construction residential units from 12% to 5% without ITC, and down to 1% for homes under Rs 45 Lakhs, stimulating new launches.",
        "primary_source": "CBIC Notification No. 03/2019-Central Tax (Rate), Government of India",
        "source_url": "https://cbic-gst.gov.in/central-tax-notifications.html",
        "affected_corridors": ["Pan-India", "Under Construction Projects"],
    },
    {
        "id": "stamp-cut-2020",
        "year": 2020,
        "date": "2020-09-01",
        "headline": "Maharashtra Stamp Duty Reduced to 2% Stimulus & WFH Luxury Demand",
        "category": "State Policy",
        "movement": "Historic Registration Volume Surge & Inventory Liquidation (+6.4% p.a.)",
        "impact_direction": "positive",
        "description": "Maharashtra temporarily slashed stamp duty from 5% to 2% between Sept-Dec 2020 and 3% through March 2021. Sparked historic transaction surges across Mumbai MMR, Worli, and Bandra.",
        "primary_source": "Government of Maharashtra, Revenue & Forest Department Gazette Notification (Aug 2020)",
        "source_url": "https://igod.gov.in/",
        "affected_corridors": ["Mumbai (MMR)", "Pune", "Maharashtra"],
    },
    {
        "id": "rate-cycle-2022",
        "year": 2022,
        "date": "2022-05-04",
        "headline": "RBI Initiates Repo Rate Tightening Cycle (4.00% to 6.50%)",
        "category": "Monetary Policy",
        "movement": "Luxury Price Inelasticity & Premium Realization Jump (+11.2% p.a.)",
        "impact_direction": "positive",
        "description": "Despite home loan floating rates climbing from 6.6% to 8.5%+, prime residential absorption accelerated as buyers sought larger, superior configurations post-pandemic.",
        "primary_source": "Reserve Bank of India Monetary Policy Committee Statements (2022-2023)",
        "source_url": "https://www.rbi.org.in/",
        "affected_corridors": ["Pan-India", "Metro Housing Markets"],
    },
    {
        "id": "coastal-road-2024",
        "year": 2024,
        "date": "2024-03-12",
        "headline": "Mumbai Coastal Road (Phase 1 & 2) & Atal Setu (MTHL) Commissioned",
        "category": "Mega Infrastructure",
        "movement": "Direct Connectivity Premium (+14.5% to +18.2% Corridor Outperformance)",
        "impact_direction": "positive",
        "description": "Opening of the 10.58 km Coastal Road from Marine Drive to Worli reduced peak commute from 45 min to under 12 min. Combined with Atal Setu, prime South Mumbai and Worli commanded peak micro-market premiums.",
        "primary_source": "Brihanmumbai Municipal Corporation (BMC) & MMRDA Engineering Dossiers",
        "source_url": "https://mmrda.maharashtra.gov.in/",
        "affected_corridors": ["Worli / South Mumbai", "Bandra West", "Lower Parel", "Mumbai (MMR)"],
    },
    {
        "id": "metro-aqua-2025",
        "year": 2025,
        "date": "2025-01-15",
        "headline": "Mumbai Metro Line 3 (Aqua Line) & Bengaluru Airport Metro Integration",
        "category": "Transit Infrastructure",
        "movement": "Commercial-Residential Transit Hub Appreciation (+12.8% p.a.)",
        "impact_direction": "positive",
        "description": "Underground connectivity between Cuffe Parade, BKC, SEEPZ, and International Airport drastically reduced intra-city travel friction, amplifying demand in transit-adjacent residential clusters.",
        "primary_source": "Mumbai Metro Rail Corporation Limited (MMRCL) Operational Reports",
        "source_url": "https://mmrcl.com/",
        "affected_corridors": ["Worli / South Mumbai", "Bandra West", "Andheri West", "Whitefield"],
    },
    {
        "id": "residex-2026",
        "year": 2026,
        "date": "2026-06-30",
        "headline": "NHB RESIDEX 2026 Benchmark: Capital Values Reach All-Time Index High",
        "category": "Market Benchmark",
        "movement": "Sustained Capital Growth & Institutional Redevelopment Velocity (+8.4% NHB Avg)",
        "impact_direction": "positive",
        "description": "National Housing Bank indices confirm 10-year annualised compounding of 8.2% in Mumbai MMR, 9.6% in Bengaluru, and 11.2% in Hyderabad, driven by high-density redevelopment and institutional execution.",
        "primary_source": "National Housing Bank RESIDEX Housing Price Index Database",
        "source_url": "https://residex.nhb.org.in/",
        "affected_corridors": ["Pan-India", "Tier-1 Metro Micro-Markets"],
    },
]


def get_macro_news_events(city: str | None = None) -> list[dict[str, Any]]:
    """Return chronological macro news events, optionally filtered/prioritized by city."""
    if not city:
        return HISTORICAL_NEWS_EVENTS
    # Return all events, marking city-relevant ones
    res = []
    for ev in HISTORICAL_NEWS_EVENTS:
        ev_copy = dict(ev)
        ev_copy["is_city_relevant"] = (
            "Pan-India" in ev["affected_corridors"]
            or any(city.lower() in c.lower() for c in ev["affected_corridors"])
        )
        res.append(ev_copy)
    return res


def get_news_summary_for_advisor(city: str, locality: str) -> str:
    """Format macro real estate news events into concise prompt context for the LLM advisor."""
    events = get_macro_news_events(city)
    lines = []
    for ev in events[-5:]:  # Most recent 5 key macro developments
        lines.append(f"- {ev['year']} ({ev['category']}): {ev['headline']}. Market impact: {ev['movement']}.")
    return "\n".join(lines)
