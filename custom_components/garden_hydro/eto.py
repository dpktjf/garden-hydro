"""Evapotranspiration helper functions."""

from __future__ import annotations

from math import sqrt
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
    * ETo = 0.0023 × (Tmean + 17.8) × sqrt(Tmax − Tmin) × Ra
    """
    delta = tmax_c - tmin_c
    if delta <= 0:
        return 0.0

    tmean = (tmin_c + tmax_c) / 2.0
    eto = 0.0023 * (tmean + 17.8) * sqrt(delta) * ra_mj_m2_day
    return max(0.0, eto)
