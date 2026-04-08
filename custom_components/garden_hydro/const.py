"""Constants for the Garden Hydro integration."""

from __future__ import annotations

from datetime import time
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
CONF_HUMIDITY_ENTITY_ID: Final = "humidity_entity_id"
CONF_WIND_SPEED_ENTITY_ID: Final = "wind_speed_entity_id"
CONF_SOLAR_RADIATION_ENTITY_ID: Final = "solar_radiation_entity_id"
CONF_LATITUDE: Final = "latitude"
CONF_ELEVATION: Final = "elevation"
CONF_ENABLE_HARGREAVES: Final = "enable_hargreaves"
CONF_ENABLE_PENMAN_MONTEITH: Final = "enable_penman_monteith"

DEFAULT_SITE_NAME: Final = NAME
DEFAULT_ROLLUP_TIME: Final = time(hour=3, minute=0)
CALC_MODE: Final = "calc_mode"
CALC_MODE_HARGREAVES: Final = "hargreaves_london_ra_blend"
CALC_MODE_PENMAN_MONTEITH: Final = "penman_monteith_daily"

SERVICE_RECALCULATE_SITE: Final = "recalculate_site"
ATTR_ENTRY_ID: Final = "entry_id"

WEATHER_OK: Final = "ok"
WEATHER_PARTIAL: Final = "partial"
WEATHER_MISSING_TMIN: Final = "missing_tmin"
WEATHER_MISSING_TMAX: Final = "missing_tmax"
WEATHER_MISSING_RAIN: Final = "missing_rain"
WEATHER_MISSING_HUMIDITY: Final = "missing_humidity"
WEATHER_MISSING_WIND_SPEED: Final = "missing_wind_speed"
WEATHER_MISSING_SOLAR_RADIATION: Final = "missing_solar_radiation"
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
UNIT_PERCENT: Final = "%"
UNIT_METERS_PER_SECOND: Final = "m/s"
UNIT_METERS: Final = "m"
UNIT_DEGREES: Final = "°"

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
ACCEPTED_HUMIDITY_UNITS: Final[set[str | None]] = {
    None,
    "%",
}
ACCEPTED_WIND_SPEED_UNITS: Final[set[str | None]] = {
    None,
    "m/s",
    "mps",
}
ACCEPTED_SOLAR_RADIATION_UNITS: Final[set[str | None]] = {
    None,
    "MJ/m²/day",
    "MJ/m2/day",
}

MIN_TEMP_C: Final = -40.0
MAX_TEMP_C: Final = 60.0
MAX_RAIN_MM: Final = 500.0
MAX_FORECAST_RAIN_MM: Final = 500.0
MAX_HUMIDITY_PCT: Final = 100.0
MAX_WIND_SPEED_M_S: Final = 100.0
MAX_SOLAR_RADIATION_MJ_M2_DAY: Final = 60.0
MIN_LATITUDE: Final = -90.0
MAX_LATITUDE: Final = 90.0
MIN_ELEVATION_M: Final = -500.0
MAX_ELEVATION_M: Final = 10000.0
