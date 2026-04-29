"""Runtime models for the Garden Hydro integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(slots=True)
class ZoneSettings:
    """Mutable runtime settings for one watering zone."""

    zone_name: str
    zone_slug: str
    enabled: bool = False
    eto_source: str = "hargreaves"
    border_type: str = "mixed_established"
    border_factor: float = 0.75
    application_rate_mm_per_hr: float = 12.0
    max_runtime_min: float = 30.0
    rain_effective_pct: float = 80.0
    forecast_credit_pct: float = 50.0
    irrigation_efficiency_pct: float = 90.0
    manual_adjustment_pct: float = 0.0


@dataclass(slots=True)
class ZoneCalculationResult:
    """Advisory watering calculation for one watering zone."""

    eto_source: str | None = None
    selected_eto_mm: float | None = None
    border_factor: float | None = None
    zone_eto_mm: float | None = None
    adjusted_need_mm: float | None = None
    effective_rain_mm: float | None = None
    forecast_credit_mm: float | None = None
    water_required_mm: float | None = None
    recommended_runtime_min: float | None = None
    status: str | None = None


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
    zone_results: dict[str, ZoneCalculationResult] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeData:
    """Mutable runtime state shared between platforms."""

    ra_values: dict[str, float]
    result: SiteCalculationResult = field(default_factory=SiteCalculationResult)
    zone_settings: dict[str, ZoneSettings] = field(default_factory=dict)
