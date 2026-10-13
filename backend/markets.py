"""Market reference: cities, states, and localities with coordinates.

Read from backend/data/markets.json. The file is the single source for the
locality dropdowns and the coordinates the model uses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache

from backend.config import MARKETS_PATH


@dataclass(frozen=True)
class Locality:
    name: str
    city: str
    state: str
    lat: float
    lon: float
    premium: float


@dataclass(frozen=True)
class City:
    name: str
    state: str
    base_psf: float
    source: str
    localities: tuple[Locality, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MarketIndex:
    provenance: str
    cities: dict[str, City]
    localities: dict[tuple[str, str], Locality]  # (city, locality) -> Locality

    def city_names(self) -> list[str]:
        return sorted(self.cities)

    def locality_names(self, city: str) -> list[str]:
        return [loc.name for loc in self.cities[city].localities]


def _build(raw: dict) -> MarketIndex:
    cities: dict[str, City] = {}
    localities: dict[tuple[str, str], Locality] = {}
    for c in raw["cities"]:
        locs = []
        for l in c["localities"]:
            loc = Locality(
                name=l["name"],
                city=c["name"],
                state=l.get("state", c["state"]),
                lat=float(l["lat"]),
                lon=float(l["lon"]),
                premium=float(l["premium"]),
            )
            locs.append(loc)
            localities[(c["name"], loc.name)] = loc
        cities[c["name"]] = City(
            name=c["name"],
            state=c["state"],
            base_psf=float(c["base_psf"]),
            source=c["source"],
            localities=tuple(locs),
        )
    return MarketIndex(
        provenance=raw.get("_provenance", ""),
        cities=cities,
        localities=localities,
    )


@lru_cache(maxsize=1)
def load_markets(path: str | None = None) -> MarketIndex:
    """Load and index the market reference. Cached for the process lifetime."""
    target = path or str(MARKETS_PATH)
    with open(target, encoding="utf-8") as fh:
        raw = json.load(fh)
    return _build(raw)
