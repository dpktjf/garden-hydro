"""Runtime models for the Garden Hydro integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(slots=True)
class SiteCalculationResult:
    """Latest calculated or restored site-level state."""

    eto_hargreaves_mm: float | None = None
    eto_penman_monteith_mm: float | None = None
    daily_eto_mm: float | None = None
    daily_rain_mm: float | None = None
    forecast_rain_mm: float | None = None
    last_rollup: datetime | None = None
    last_calculation: datetime | None = None
    calc_mode: str | None = None
    tmin_c: float | None = None
    tmax_c: float | None = None
    humidity_pct: float | None = None
    wind_speed_m_s: float | None = None
    solar_radiation_mj_m2_day: float | None = None
    latitude: float | None = None
    elevation_m: float | None = None
    ra_used_mj_m2_day: float | None = None
    weather_status: str | None = None
    calculation_date: str | None = None
    is_scheduled: bool = False
    source_tmin_entity_id: str | None = None
    source_tmax_entity_id: str | None = None
    source_rain_entity_id: str | None = None
    source_forecast_rain_entity_id: str | None = None
    tmean_c: float | None = None
    temperature_delta_c: float | None = None
    hargreaves_status: str | None = None
    penman_monteith_status: str | None = None


@dataclass(slots=True)
class RuntimeData:
    """Mutable runtime state shared between platforms."""

    ra_values: dict[str, float]
    result: SiteCalculationResult = field(default_factory=SiteCalculationResult)
