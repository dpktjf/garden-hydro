"""Coordinator for Garden Hydro site calculations."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, time, timedelta
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    ACCEPTED_RAIN_UNITS,
    ACCEPTED_TEMP_UNITS,
    CALC_MODE,
    CONF_FORECAST_RAIN_ENTITY_ID,
    CONF_RAIN_ENTITY_ID,
    CONF_ROLLUP_TIME,
    CONF_TMAX_ENTITY_ID,
    CONF_TMIN_ENTITY_ID,
    DEFAULT_ROLLUP_TIME,
    MAX_FORECAST_RAIN_MM,
    MAX_RAIN_MM,
    MAX_TEMP_C,
    MIN_TEMP_C,
    WEATHER_INVALID_NUMERIC_INPUT,
    WEATHER_INVALID_TEMPERATURE_RANGE,
    WEATHER_MISSING_RAIN,
    WEATHER_MISSING_TMAX,
    WEATHER_MISSING_TMIN,
    WEATHER_OK,
)
from .eto import blended_ra_for_date, calculate_hargreaves_eto
from .models import RuntimeData, SiteCalculationResult

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

    def _calculate(
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
        ra_used = blended_ra_for_date(calculation_date, self.runtime.ra_values)
        eto_mm = calculate_hargreaves_eto(tmin, tmax, ra_used)
        tmean = (tmin + tmax) / 2.0
        temperature_delta = tmax - tmin

        last_rollup = now if is_scheduled else self.runtime.result.last_rollup
        return SiteCalculationResult(
            daily_eto_mm=eto_mm,
            daily_rain_mm=rain,
            forecast_rain_mm=forecast_rain,
            last_rollup=last_rollup,
            last_calculation=now,
            calc_mode=CALC_MODE,
            tmin_c=tmin,
            tmax_c=tmax,
            ra_used_mj_m2_day=ra_used,
            weather_status=WEATHER_OK,
            calculation_date=calculation_date.isoformat(),
            is_scheduled=is_scheduled,
            source_tmin_entity_id=self.config[CONF_TMIN_ENTITY_ID],
            source_tmax_entity_id=self.config[CONF_TMAX_ENTITY_ID],
            source_rain_entity_id=self.config[CONF_RAIN_ENTITY_ID],
            source_forecast_rain_entity_id=forecast_entity_id,
            tmean_c=tmean,
            temperature_delta_c=temperature_delta,
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
        return replace(
            previous_result,
            last_calculation=now,
            weather_status=weather_status,
            is_scheduled=is_scheduled,
            calc_mode=CALC_MODE,
        )

    def _read_required_numeric(
        self,
        entity_id: str,
        *,
        accepted_units: set[str | None],
        missing_status: str,
        min_value: float,
        max_value: float,
    ) -> float | str:
        """Read and validate a required numeric entity value."""
        state = self.hass.states.get(entity_id)
        if state is None or state.state in _MISSING_STATES:
            return missing_status

        unit = state.attributes.get("unit_of_measurement")
        if unit not in accepted_units:
            return WEATHER_INVALID_NUMERIC_INPUT

        try:
            value = float(state.state)
        except (TypeError, ValueError):
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

        if value < min_value or value > max_value:
            return None

        return value
