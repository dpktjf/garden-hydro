"""Constants for the Garden Hydro integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "garden_hydro"
NAME: Final = "DPK Garden Hydro"
VERSION: Final = "0.1.1"

PLATFORMS: Final[list[str]] = ["sensor", "number"]

CONF_SITE_NAME: Final = "site_name"
CONF_ROLLUP_TIME: Final = "rollup_time"
CONF_TMIN_ENTITY_ID: Final = "tmin_entity_id"
CONF_TMAX_ENTITY_ID: Final = "tmax_entity_id"
CONF_RAIN_ENTITY_ID: Final = "rain_entity_id"
CONF_FORECAST_RAIN_ENTITY_ID: Final = "forecast_rain_entity_id"

DEFAULT_SITE_NAME: Final = NAME
DEFAULT_ROLLUP_TIME: Final = "03:00"
CALC_MODE: Final = "hargreaves_london_ra_blend"

SERVICE_RECALCULATE_SITE: Final = "recalculate_site"
ATTR_ENTRY_ID: Final = "entry_id"

WEATHER_OK: Final = "ok"
WEATHER_MISSING_TMIN: Final = "missing_tmin"
WEATHER_MISSING_TMAX: Final = "missing_tmax"
WEATHER_MISSING_RAIN: Final = "missing_rain"
WEATHER_INVALID_TEMPERATURE_RANGE: Final = "invalid_temperature_range"
WEATHER_INVALID_NUMERIC_INPUT: Final = "invalid_numeric_input"
WEATHER_ROLLUP_SKIPPED: Final = "rollup_skipped"

RA_DEFAULTS: Final[dict[str, float]] = {
    "jan": 8.0,
    "feb": 13.5,
    "mar": 21.4,
    "apr": 31.0,
    "may": 38.3,
    "jun": 41.6,
    "jul": 40.1,
    "aug": 33.9,
    "sep": 24.9,
    "oct": 16.0,
    "nov": 9.3,
    "dec": 6.6,
}

MONTH_KEYS: Final[tuple[str, ...]] = tuple(RA_DEFAULTS)
MONTH_INDEX_TO_KEY: Final[dict[int, str]] = {
    1: "jan",
    2: "feb",
    3: "mar",
    4: "apr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "aug",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dec",
}

UNIT_MILLIMETERS: Final = "mm"
UNIT_MJ_M2_DAY: Final = "MJ/m²/day"

# Phase 1 deliberately accepts only a narrow set of units.
ACCEPTED_TEMP_UNITS: Final[set[str | None]] = {
    None,
    "°C",
    "° C",
    "C",
    "c",
    "celsius",
    "°c",
}
ACCEPTED_RAIN_UNITS: Final[set[str | None]] = {
    None,
    "mm",
    "millimeter",
    "millimeters",
}

MIN_TEMP_C: Final = -40.0
MAX_TEMP_C: Final = 60.0
MAX_RAIN_MM: Final = 500.0
MAX_FORECAST_RAIN_MM: Final = 500.0
