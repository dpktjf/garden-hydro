"""Evapotranspiration helper functions."""

from __future__ import annotations

from math import acos, cos, exp, pi, sin, sqrt, tan
from typing import TYPE_CHECKING

from .const import MONTH_INDEX_TO_KEY

if TYPE_CHECKING:
    from datetime import date

MONTHS_IN_YEAR = 12
MID_MONTH_DAY = 15


def blended_ra_for_date(day: date, ra_values: dict[str, float]) -> float:
    """
    Return the blended monthly extraterrestrial radiation value.

    The integration uses a simple month-to-month smoothing rule:
    * on or before the 15th, average the previous and current month
    * after the 15th, average the current and next month
    """
    current_key = MONTH_INDEX_TO_KEY[day.month]
    previous_month = MONTHS_IN_YEAR if day.month == 1 else day.month - 1
    next_month = 1 if day.month == MONTHS_IN_YEAR else day.month + 1
    previous_key = MONTH_INDEX_TO_KEY[previous_month]
    next_key = MONTH_INDEX_TO_KEY[next_month]

    if day.day <= MID_MONTH_DAY:
        return (ra_values[previous_key] + ra_values[current_key]) / 2.0

    return (ra_values[current_key] + ra_values[next_key]) / 2.0


def calculate_hargreaves_eto(
    tmin_c: float,
    tmax_c: float,
    ra_mj_m2_day: float,
) -> float:
    """
    Calculate daily reference evapotranspiration in mm/day.

    The Phase 1 site engine uses the reduced-data Hargreaves equation:
    * ETo = 0.0023 * (Tmean + 17.8) * sqrt(Tmax - Tmin) * Ra
    """
    delta = tmax_c - tmin_c
    if delta <= 0:
        return 0.0

    tmean = (tmin_c + tmax_c) / 2.0
    eto = 0.0023 * (tmean + 17.8) * sqrt(delta) * ra_mj_m2_day
    return max(0.0, eto)


def _saturation_vapor_pressure(temp_c: float) -> float:
    """Return saturation vapor pressure in kPa."""
    return 0.6108 * exp((17.27 * temp_c) / (temp_c + 237.3))


def _slope_vapor_pressure_curve(temp_c: float) -> float:
    """Return slope of saturation vapor pressure curve in kPa/°C."""
    es = _saturation_vapor_pressure(temp_c)
    return 4098.0 * es / ((temp_c + 237.3) ** 2)


def _atmospheric_pressure_kpa(elevation_m: float) -> float:
    """Return atmospheric pressure in kPa from elevation."""
    return 101.3 * (((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26)


def calculate_penman_monteith_eto(  # noqa: PLR0913
    *,
    tmin_c: float,
    tmax_c: float,
    humidity_pct: float,
    wind_speed_m_s: float,
    solar_radiation_mj_m2_day: float,
    elevation_m: float,
    latitude_deg: float,
    day: date,
) -> float:
    """
    Calculate daily FAO-56 Penman-Monteith ETo in mm/day.

    This is a minimum viable daily implementation using:
    - Tmin/Tmax
    - mean relative humidity
    - mean wind speed at 2 m
    - daily solar radiation
    - elevation
    - latitude
    - date
    """
    tmean_c = (tmin_c + tmax_c) / 2.0
    delta = _slope_vapor_pressure_curve(tmean_c)

    es_tmin = _saturation_vapor_pressure(tmin_c)
    es_tmax = _saturation_vapor_pressure(tmax_c)
    es = (es_tmin + es_tmax) / 2.0
    ea = (humidity_pct / 100.0) * es

    pressure_kpa = _atmospheric_pressure_kpa(elevation_m)
    gamma = 0.000665 * pressure_kpa

    # Extraterrestrial radiation from date/latitude for clear-sky radiation.
    lat_rad = latitude_deg * pi / 180.0
    dr = 1.0 + 0.033 * cos((2.0 * pi / 365.0) * day.timetuple().tm_yday)
    solar_declination = 0.409 * sin((2.0 * pi / 365.0) * day.timetuple().tm_yday - 1.39)
    sunset_hour_angle = acos(-tan(lat_rad) * tan(solar_declination))
    ra = (
        (24.0 * 60.0 / pi)
        * 0.0820
        * dr
        * (
            sunset_hour_angle * sin(lat_rad) * sin(solar_declination)
            + cos(lat_rad) * cos(solar_declination) * sin(sunset_hour_angle)
        )
    )

    rso = (0.75 + 2e-5 * elevation_m) * ra
    rs = solar_radiation_mj_m2_day
    rns = (1.0 - 0.23) * rs

    tmax_k = tmax_c + 273.16
    tmin_k = tmin_c + 273.16
    rs_rso_ratio = min(1.0, rs / rso) if rso > 0 else 0.0
    rnl = (
        4.903e-9
        * (((tmax_k**4) + (tmin_k**4)) / 2.0)
        * (0.34 - 0.14 * sqrt(max(ea, 0.0)))
        * (1.35 * rs_rso_ratio - 0.35)
    )
    rn = rns - rnl

    # Soil heat flux G is assumed to be 0 for daily timestep.
    eto = (0.408 * delta * rn + gamma * (900.0 / (tmean_c + 273.0)) * wind_speed_m_s * (es - ea)) / (
        delta + gamma * (1.0 + 0.34 * wind_speed_m_s)
    )

    return max(0.0, eto)
