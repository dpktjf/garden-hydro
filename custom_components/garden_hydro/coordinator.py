"""Coordinator for Garden Hydro site calculations."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    ACCEPTED_HUMIDITY_UNITS,
    ACCEPTED_RAIN_UNITS,
    ACCEPTED_SOLAR_RADIATION_UNITS,
    ACCEPTED_TEMP_UNITS,
    ACCEPTED_WIND_SPEED_UNITS,
    CALC_MODE_HARGREAVES,
    CALC_MODE_PENMAN_MONTEITH,
    CONF_ELEVATION,
    CONF_ENABLE_HARGREAVES,
    CONF_ENABLE_PENMAN_MONTEITH,
    CONF_FORECAST_RAIN_ENTITY_ID,
    CONF_HUMIDITY_ENTITY_ID,
    CONF_LATITUDE,
    CONF_RAIN_ENTITY_ID,
    CONF_ROLLUP_TIME,
    CONF_SOLAR_RADIATION_ENTITY_ID,
    CONF_TMAX_ENTITY_ID,
    CONF_TMIN_ENTITY_ID,
    CONF_WIND_SPEED_ENTITY_ID,
    DEFAULT_ROLLUP_TIME,
    ETO_SOURCE_PENMAN_MONTEITH,
    MAX_FORECAST_RAIN_MM,
    MAX_HUMIDITY_PCT,
    MAX_RAIN_MM,
    MAX_SOLAR_RADIATION_MJ_M2_DAY,
    MAX_TEMP_C,
    MAX_WIND_SPEED_M_S,
    MIN_TEMP_C,
    WEATHER_INVALID_NUMERIC_INPUT,
    WEATHER_INVALID_TEMPERATURE_RANGE,
    WEATHER_MISSING_HUMIDITY,
    WEATHER_MISSING_RAIN,
    WEATHER_MISSING_SOLAR_RADIATION,
    WEATHER_MISSING_TMAX,
    WEATHER_MISSING_TMIN,
    WEATHER_MISSING_WIND_SPEED,
    WEATHER_OK,
    WEATHER_PARTIAL,
    ZONE_STATUS_CAPPED,
    ZONE_STATUS_DATA_UNAVAILABLE,
    ZONE_STATUS_DISABLED,
    ZONE_STATUS_NO_WATER_REQUIRED,
    ZONE_STATUS_WATER_REQUIRED,
)
from .eto import (
    blended_ra_for_date,
    calculate_hargreaves_eto,
    calculate_penman_monteith_eto,
)
from .models import RuntimeData, SiteCalculationResult, ZoneCalculationResult

if TYPE_CHECKING:
    from collections.abc import Callable

_LOGGER = logging.getLogger(__name__)

_MISSING_STATES = {"unknown", "unavailable", "none", "None"}


class GardenHydroCoordinator(DataUpdateCoordinator[SiteCalculationResult]):
    """Coordinate site-level daily weather validation and ETo calculation."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        runtime: RuntimeData,
        config: dict[str, Any],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"garden_hydro_{entry_id}",
            always_update=True,
        )
        self.entry_id = entry_id
        self.runtime = runtime
        self.config = config
        self._remove_rollup_listener: CALLBACK_TYPE | None = None
        self.async_set_updated_data(runtime.result)

    async def async_start(self) -> None:
        """Start the daily rollup scheduler."""
        self._schedule_next_rollup()

    async def async_stop(self) -> None:
        """Stop the daily rollup scheduler."""
        if self._remove_rollup_listener is not None:
            self._remove_rollup_listener()
            self._remove_rollup_listener = None

    @callback
    def _schedule_next_rollup(self) -> None:
        """Schedule the next daily rollup callback."""
        if self._remove_rollup_listener is not None:
            self._remove_rollup_listener()
            self._remove_rollup_listener = None

        next_run = self._next_rollup_datetime()
        self._remove_rollup_listener = async_track_point_in_time(
            self.hass,
            self._handle_scheduled_rollup,
            next_run,
        )
        _LOGGER.debug("Scheduled next garden_hydro rollup for %s", next_run)

    async def _handle_scheduled_rollup(self, now: datetime) -> None:
        """Run the scheduled rollup and queue the next one."""
        await self.async_run_rollup(is_scheduled=True, now=now)
        self._schedule_next_rollup()

    def _next_rollup_datetime(self) -> datetime:
        """Return the next local datetime when the rollup should run."""
        local_now = dt_util.now()
        next_run = datetime.combine(
            local_now.date(),
            self._configured_rollup_time(),
            local_now.tzinfo,
        )
        if next_run <= local_now:
            next_run += timedelta(days=1)
        return next_run

    def _configured_rollup_time(self) -> time:
        """Parse and return the configured rollup time."""
        raw_time = self.config[CONF_ROLLUP_TIME]

        # Preferred: already a time object
        if isinstance(raw_time, time):
            return raw_time.replace(second=0, microsecond=0)

        # String formats
        if isinstance(raw_time, str):
            parts = raw_time.split(":")

            if len(parts) >= 2:  # noqa: PLR2004
                try:
                    hour = int(parts[0])
                    minute = int(parts[1])

                    return time(hour=hour, minute=minute)

                except ValueError:
                    _LOGGER.warning(
                        "Invalid rollup_time value '%s'; using default %s",
                        raw_time,
                        DEFAULT_ROLLUP_TIME,
                    )

        # Fallback
        return DEFAULT_ROLLUP_TIME

    async def async_run_rollup(
        self,
        *,
        is_scheduled: bool,
        now: datetime | None = None,
    ) -> SiteCalculationResult:
        """Execute a site calculation from the mapped weather entities."""
        calculation_time = now or dt_util.now()
        result = self._calculate(now=calculation_time, is_scheduled=is_scheduled)
        self.runtime.result = result
        self.async_set_updated_data(result)
        return result

    def _calculate(  # noqa: PLR0912
        self,
        *,
        now: datetime,
        is_scheduled: bool,
    ) -> SiteCalculationResult:
        """Validate source entities and calculate the current site result."""
        tmin = self._read_required_numeric(
            self.config[CONF_TMIN_ENTITY_ID],
            accepted_units=ACCEPTED_TEMP_UNITS,
            missing_status=WEATHER_MISSING_TMIN,
            min_value=MIN_TEMP_C,
            max_value=MAX_TEMP_C,
        )
        if isinstance(tmin, str):
            return self._failed_result(
                now=now,
                is_scheduled=is_scheduled,
                weather_status=tmin,
            )

        tmax = self._read_required_numeric(
            self.config[CONF_TMAX_ENTITY_ID],
            accepted_units=ACCEPTED_TEMP_UNITS,
            missing_status=WEATHER_MISSING_TMAX,
            min_value=MIN_TEMP_C,
            max_value=MAX_TEMP_C,
        )
        if isinstance(tmax, str):
            return self._failed_result(
                now=now,
                is_scheduled=is_scheduled,
                weather_status=tmax,
            )

        if tmax < tmin:
            return self._failed_result(
                now=now,
                is_scheduled=is_scheduled,
                weather_status=WEATHER_INVALID_TEMPERATURE_RANGE,
            )

        rain = self._read_required_numeric(
            self.config[CONF_RAIN_ENTITY_ID],
            accepted_units=ACCEPTED_RAIN_UNITS,
            missing_status=WEATHER_MISSING_RAIN,
            min_value=0.0,
            max_value=MAX_RAIN_MM,
        )
        if isinstance(rain, str):
            return self._failed_result(
                now=now,
                is_scheduled=is_scheduled,
                weather_status=rain,
            )

        forecast_rain: float | None = None
        forecast_entity_id = self.config.get(CONF_FORECAST_RAIN_ENTITY_ID)
        if forecast_entity_id:
            forecast_rain = self._read_optional_numeric(
                forecast_entity_id,
                accepted_units=ACCEPTED_RAIN_UNITS,
                min_value=0.0,
                max_value=MAX_FORECAST_RAIN_MM,
            )

        calculation_date = now.date()
        ra_used = blended_ra_for_date(now.date(), self.runtime.ra_values)
        enabled_modes: list[str] = []
        if self.config.get(CONF_ENABLE_HARGREAVES, True):
            enabled_modes.append(CALC_MODE_HARGREAVES)
        if self.config.get(CONF_ENABLE_PENMAN_MONTEITH, True):
            enabled_modes.append(CALC_MODE_PENMAN_MONTEITH)

        eto_hargreaves_mm: float | None = None
        eto_penman_monteith_mm: float | None = None
        hargreaves_status: str = "disabled"
        penman_status: str = "disabled"
        humidity: float | None = None
        wind_speed: float | None = None
        solar_radiation: float | None = None

        if self.config.get(CONF_ENABLE_HARGREAVES, True):
            eto_hargreaves_mm = calculate_hargreaves_eto(
                tmin_c=tmin,
                tmax_c=tmax,
                ra_mj_m2_day=ra_used,
            )
            hargreaves_status = WEATHER_OK

        if self.config.get(CONF_ENABLE_PENMAN_MONTEITH, True):
            humidity_result = self._read_required_numeric(
                self.config[CONF_HUMIDITY_ENTITY_ID],
                accepted_units=ACCEPTED_HUMIDITY_UNITS,
                missing_status=WEATHER_MISSING_HUMIDITY,
                min_value=0.0,
                max_value=MAX_HUMIDITY_PCT,
            )
            wind_result = self._read_required_numeric(
                self.config[CONF_WIND_SPEED_ENTITY_ID],
                accepted_units=ACCEPTED_WIND_SPEED_UNITS,
                missing_status=WEATHER_MISSING_WIND_SPEED,
                min_value=0.0,
                max_value=MAX_WIND_SPEED_M_S,
                converter=_normalize_wind_speed,
            )
            solar_result = self._read_required_numeric(
                self.config[CONF_SOLAR_RADIATION_ENTITY_ID],
                accepted_units=ACCEPTED_SOLAR_RADIATION_UNITS,
                missing_status=WEATHER_MISSING_SOLAR_RADIATION,
                min_value=0.0,
                max_value=MAX_SOLAR_RADIATION_MJ_M2_DAY,
                converter=_normalize_solar_radiation,
            )

            if (
                not isinstance(humidity_result, str)
                and not isinstance(wind_result, str)
                and not isinstance(solar_result, str)
            ):
                humidity = humidity_result
                wind_speed = wind_result
                solar_radiation = solar_result
                eto_penman_monteith_mm = calculate_penman_monteith_eto(
                    tmin_c=tmin,
                    tmax_c=tmax,
                    humidity_pct=humidity,
                    wind_speed_m_s=wind_speed,
                    solar_radiation_mj_m2_day=solar_radiation,
                    elevation_m=float(self.config[CONF_ELEVATION]),
                    latitude_deg=float(self.config[CONF_LATITUDE]),
                    day=now.date(),
                )
                penman_status = WEATHER_OK
            else:
                penman_status = (
                    WEATHER_INVALID_NUMERIC_INPUT
                    if any(
                        value == WEATHER_INVALID_NUMERIC_INPUT
                        for value in (humidity_result, wind_result, solar_result)
                        if isinstance(value, str)
                    )
                    else WEATHER_PARTIAL
                )

        weather_status = WEATHER_OK
        if WEATHER_OK not in (hargreaves_status, penman_status):
            weather_status = WEATHER_INVALID_NUMERIC_INPUT
        elif hargreaves_status != WEATHER_OK or penman_status != WEATHER_OK:
            weather_status = WEATHER_PARTIAL

        tmean = (tmin + tmax) / 2.0
        temperature_delta = tmax - tmin

        last_rollup = now if is_scheduled else self.runtime.result.last_rollup
        return SiteCalculationResult(
            eto_hargreaves_mm=(round(eto_hargreaves_mm, 2) if eto_hargreaves_mm is not None else None),
            eto_penman_monteith_mm=(round(eto_penman_monteith_mm, 2) if eto_penman_monteith_mm is not None else None),
            daily_eto_mm=(round(eto_hargreaves_mm, 2) if eto_hargreaves_mm is not None else None),
            daily_rain_mm=rain,
            forecast_rain_mm=forecast_rain,
            last_rollup=last_rollup,
            last_calculation=now,
            calc_mode=",".join(enabled_modes),
            tmin_c=tmin,
            tmax_c=tmax,
            humidity_pct=round(humidity, 1) if humidity is not None else None,
            wind_speed_m_s=round(wind_speed, 2) if wind_speed is not None else None,
            solar_radiation_mj_m2_day=(round(solar_radiation, 2) if solar_radiation is not None else None),
            latitude=float(self.config[CONF_LATITUDE]),
            elevation_m=float(self.config[CONF_ELEVATION]),
            ra_used_mj_m2_day=ra_used,
            weather_status=weather_status,
            calculation_date=calculation_date.isoformat(),
            is_scheduled=is_scheduled,
            hargreaves_status=hargreaves_status,
            penman_monteith_status=penman_status,
            source_tmin_entity_id=self.config[CONF_TMIN_ENTITY_ID],
            source_tmax_entity_id=self.config[CONF_TMAX_ENTITY_ID],
            source_rain_entity_id=self.config[CONF_RAIN_ENTITY_ID],
            source_forecast_rain_entity_id=forecast_entity_id,
            tmean_c=tmean,
            temperature_delta_c=temperature_delta,
            zone_results=self._calculate_zone_results(
                eto_hargreaves_mm=eto_hargreaves_mm,
                eto_penman_monteith_mm=eto_penman_monteith_mm,
                rain_mm=rain,
                forecast_rain_mm=forecast_rain,
            ),
        )

    def _failed_result(
        self,
        *,
        now: datetime,
        is_scheduled: bool,
        weather_status: str,
    ) -> SiteCalculationResult:
        """Return the previous result with updated failure metadata."""
        previous_result = self.runtime.result
        enabled_modes: list[str] = []
        if self.config.get(CONF_ENABLE_HARGREAVES, True):
            enabled_modes.append(CALC_MODE_HARGREAVES)
        if self.config.get(CONF_ENABLE_PENMAN_MONTEITH, True):
            enabled_modes.append(CALC_MODE_PENMAN_MONTEITH)
        return replace(
            previous_result,
            last_calculation=now,
            weather_status=weather_status,
            is_scheduled=is_scheduled,
            calc_mode=",".join(enabled_modes),
        )

    def _calculate_zone_results(
        self,
        *,
        eto_hargreaves_mm: float | None,
        eto_penman_monteith_mm: float | None,
        rain_mm: float,
        forecast_rain_mm: float | None,
    ) -> dict[str, ZoneCalculationResult]:
        """Calculate advisory watering outputs for configured zones."""
        results: dict[str, ZoneCalculationResult] = {}

        for zone_slug, settings in self.runtime.zone_settings.items():
            if not settings.enabled:
                results[zone_slug] = ZoneCalculationResult(
                    eto_source=settings.eto_source,
                    status=ZONE_STATUS_DISABLED,
                )

                continue

            selected_eto = (
                eto_penman_monteith_mm if settings.eto_source == ETO_SOURCE_PENMAN_MONTEITH else eto_hargreaves_mm
            )
            if selected_eto is None:
                results[zone_slug] = ZoneCalculationResult(
                    eto_source=settings.eto_source,
                    status=ZONE_STATUS_DATA_UNAVAILABLE,
                )
                continue

            zone_eto = selected_eto * settings.border_factor
            adjusted_need = max(
                zone_eto * (1 + settings.manual_adjustment_pct / 100),
                0,
            )
            effective_rain = rain_mm * settings.rain_effective_pct / 100
            forecast_credit = (forecast_rain_mm or 0) * settings.forecast_credit_pct / 100
            water_required = max(
                adjusted_need - effective_rain - forecast_credit,
                0,
            )
            runtime_min = (
                60 * water_required / settings.application_rate_mm_per_hr
                if settings.application_rate_mm_per_hr > 0
                else 0
            )
            recommended_runtime = min(runtime_min, settings.max_runtime_min)

            status = (
                ZONE_STATUS_NO_WATER_REQUIRED
                if water_required <= 0
                else ZONE_STATUS_CAPPED
                if runtime_min > settings.max_runtime_min
                else ZONE_STATUS_WATER_REQUIRED
            )
            results[zone_slug] = ZoneCalculationResult(
                eto_source=settings.eto_source,
                selected_eto_mm=round(selected_eto, 2),
                border_factor=round(settings.border_factor, 2),
                zone_eto_mm=round(zone_eto, 2),
                adjusted_need_mm=round(adjusted_need, 2),
                effective_rain_mm=round(effective_rain, 2),
                forecast_credit_mm=round(forecast_credit, 2),
                water_required_mm=round(water_required, 2),
                recommended_runtime_min=round(recommended_runtime, 1),
                status=status,
            )

        return results

    def _read_required_numeric(  # noqa: PLR0913
        self,
        entity_id: str,
        *,
        accepted_units: set[str | None],
        missing_status: str,
        min_value: float,
        max_value: float,
        converter: Callable[[float | None, str | None], float | None] | None = None,
    ) -> float | str:
        """Read and validate a required numeric entity value."""
        state = self.hass.states.get(entity_id)
        self.logger.debug(
            "Reading entity '%s': state=%s, attributes=%s",
            entity_id,
            state.state if state else None,
            state.attributes if state else None,
        )
        if state is None or state.state in _MISSING_STATES:
            return missing_status

        unit = state.attributes.get("unit_of_measurement")
        if unit not in accepted_units:
            return WEATHER_INVALID_NUMERIC_INPUT

        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return WEATHER_INVALID_NUMERIC_INPUT

        if converter is not None:
            value = converter(value, unit)
            if value is None:
                return WEATHER_INVALID_NUMERIC_INPUT

        if value < min_value or value > max_value:
            return WEATHER_INVALID_NUMERIC_INPUT

        return value

    def _read_optional_numeric(
        self,
        entity_id: str,
        *,
        accepted_units: set[str | None],
        min_value: float,
        max_value: float,
        converter: Callable[[float | None, str | None], float | None] | None = None,
    ) -> float | None:
        """Read and validate an optional numeric entity value."""
        state = self.hass.states.get(entity_id)
        if state is None or state.state in _MISSING_STATES:
            return None

        unit = state.attributes.get("unit_of_measurement")
        if unit not in accepted_units:
            return None

        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return None

        if converter is not None:
            value = converter(value, unit)
            if value is None:
                return None

        if value < min_value or value > max_value:
            return None

        return value


def _normalize_wind_speed(
    value: float | None,
    unit: str | None,
) -> float | None:
    """
    Convert wind speed to meters per second.

    Supported input units:
        - m/s
        - km/h
        - mph
        - kt (knots)
        - kn

    Returns:
        Wind speed in m/s, or None if value is invalid.

    """
    if value is None:
        return None

    if unit in (None, "m/s"):
        return value

    if unit == "km/h":
        return value / 3.6

    if unit == "mph":
        return value * 0.44704

    if unit in ("kt", "kn", "knots"):
        return value * 0.514444

    _LOGGER.warning(
        "Unsupported wind speed unit '%s'",
        unit,
    )

    return None


def _normalize_solar_radiation(
    value: float | None,
    unit: str | None,
) -> float | None:
    """
    Convert solar radiation to MJ/m²/day.

    Supported input units:
        - MJ/m²/day
        - MJ/m2/day
        - W/m²
        - W/m2
        - Wh/m²
        - Wh/m2
        - kWh/m²
        - kWh/m2

    Notes:
        W/m² is treated as a daily-average irradiance and converted using:
        MJ/m²/day = W/m² * 0.0864

    """
    if value is None:
        return None

    if unit in (None, "MJ/m²/day", "MJ/m2/day"):
        return value

    if unit in ("W/m²", "W/m2"):
        return value * 0.0864

    if unit in ("Wh/m²", "Wh/m2"):
        return value / 277.7778

    if unit in ("kWh/m²", "kWh/m2"):
        return value * 3.6

    _LOGGER.warning(
        "Unsupported solar radiation unit '%s'",
        unit,
    )

    return None
