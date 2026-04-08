"""Config flow for the Garden Hydro integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ELEVATION,
    CONF_ENABLE_HARGREAVES,
    CONF_ENABLE_PENMAN_MONTEITH,
    CONF_FORECAST_RAIN_ENTITY_ID,
    CONF_HUMIDITY_ENTITY_ID,
    CONF_LATITUDE,
    CONF_RAIN_ENTITY_ID,
    CONF_ROLLUP_TIME,
    CONF_SITE_NAME,
    CONF_SOLAR_RADIATION_ENTITY_ID,
    CONF_TMAX_ENTITY_ID,
    CONF_TMIN_ENTITY_ID,
    CONF_WIND_SPEED_ENTITY_ID,
    DEFAULT_ROLLUP_TIME,
    DEFAULT_SITE_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class GardenHydroConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Garden Hydro config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the first step of the configuration flow."""
        _LOGGER.debug("Entered async_step_user with input: %s", user_input)

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if user_input is not None:
            site_name = str(user_input[CONF_SITE_NAME]).strip()
            if not site_name:
                errors[CONF_SITE_NAME] = "site_name_required"
            elif not user_input[CONF_ENABLE_HARGREAVES] and not user_input[CONF_ENABLE_PENMAN_MONTEITH]:
                errors["base"] = "at_least_one_engine_required"
            else:
                self._data.update(user_input)
                self._data[CONF_SITE_NAME] = site_name
                self._data[CONF_LATITUDE] = self.hass.config.latitude
                self._data[CONF_ELEVATION] = self.hass.config.elevation
                return await self.async_step_weather_mapping()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SITE_NAME,
                        default=DEFAULT_SITE_NAME,
                    ): selector.TextSelector(),
                    vol.Required(
                        CONF_ROLLUP_TIME,
                        default=DEFAULT_ROLLUP_TIME,
                    ): selector.TimeSelector(),
                    vol.Required(
                        CONF_ENABLE_HARGREAVES,
                        default=True,
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONF_ENABLE_PENMAN_MONTEITH,
                        default=True,
                    ): selector.BooleanSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_weather_mapping(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the weather-entity mapping step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._validate_weather_mapping(user_input)
            if not errors:
                self._data.update(user_input)
                return self.async_create_entry(
                    title=self._data[CONF_SITE_NAME],
                    data=self._data,
                )

        return self.async_show_form(
            step_id="weather_mapping",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TMIN_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Required(CONF_TMAX_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Required(CONF_RAIN_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_FORECAST_RAIN_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_HUMIDITY_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_WIND_SPEED_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_SOLAR_RADIATION_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                }
            ),
            errors=errors,
        )

    @callback
    def _validate_weather_mapping(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Validate the selected weather entities before creating the entry."""
        errors: dict[str, str] = {}

        tmin_entity_id = user_input[CONF_TMIN_ENTITY_ID]
        tmax_entity_id = user_input[CONF_TMAX_ENTITY_ID]
        rain_entity_id = user_input[CONF_RAIN_ENTITY_ID]
        forecast_entity_id = user_input.get(CONF_FORECAST_RAIN_ENTITY_ID)
        humidity_entity_id = user_input.get(CONF_HUMIDITY_ENTITY_ID)
        wind_speed_entity_id = user_input.get(CONF_WIND_SPEED_ENTITY_ID)
        solar_radiation_entity_id = user_input.get(CONF_SOLAR_RADIATION_ENTITY_ID)

        if tmin_entity_id == tmax_entity_id:
            errors[CONF_TMAX_ENTITY_ID] = "tmax_must_differ"

        for key, entity_id in {
            CONF_TMIN_ENTITY_ID: tmin_entity_id,
            CONF_TMAX_ENTITY_ID: tmax_entity_id,
            CONF_RAIN_ENTITY_ID: rain_entity_id,
        }.items():
            if self.hass.states.get(entity_id) is None:
                errors[key] = "entity_not_found"

        if forecast_entity_id and self.hass.states.get(forecast_entity_id) is None:
            errors[CONF_FORECAST_RAIN_ENTITY_ID] = "entity_not_found"

        if self._data.get(CONF_ENABLE_PENMAN_MONTEITH):
            if self._data.get(CONF_LATITUDE) is None:
                errors["base"] = "latitude_required"
            if self._data.get(CONF_ELEVATION) is None:
                errors["base"] = "elevation_required"

            for key, entity_id in {
                CONF_HUMIDITY_ENTITY_ID: humidity_entity_id,
                CONF_WIND_SPEED_ENTITY_ID: wind_speed_entity_id,
                CONF_SOLAR_RADIATION_ENTITY_ID: solar_radiation_entity_id,
            }.items():
                if not entity_id:
                    errors[key] = "entity_required"
                elif self.hass.states.get(entity_id) is None:
                    errors[key] = "entity_not_found"

        return errors
