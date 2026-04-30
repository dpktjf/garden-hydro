"""Config flow for the Garden Hydro integration."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigSubentryFlow, SubentryFlowResult
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    BORDER_TYPE_FACTORS,
    BORDER_TYPE_OPTIONS,
    CONF_APPLICATION_RATE_MM_PER_HR,
    CONF_BORDER_FACTOR,
    CONF_BORDER_TYPE,
    CONF_ELEVATION,
    CONF_ENABLE_HARGREAVES,
    CONF_ENABLE_PENMAN_MONTEITH,
    CONF_ETO_SOURCE,
    CONF_FORECAST_CREDIT_PCT,
    CONF_FORECAST_RAIN_ENTITY_ID,
    CONF_HUMIDITY_ENTITY_ID,
    CONF_IRRIGATION_EFFICIENCY_PCT,
    CONF_LATITUDE,
    CONF_MANUAL_ADJUSTMENT_PCT,
    CONF_MAX_RUNTIME_MIN,
    CONF_RAIN_EFFECTIVE_PCT,
    CONF_RAIN_ENTITY_ID,
    CONF_ROLLUP_TIME,
    CONF_SITE_NAME,
    CONF_SOLAR_RADIATION_ENTITY_ID,
    CONF_TMAX_ENTITY_ID,
    CONF_TMIN_ENTITY_ID,
    CONF_WIND_SPEED_ENTITY_ID,
    CONF_ZONE_ENABLED,
    CONF_ZONE_NAME,
    CONF_ZONE_SLUG,
    DEFAULT_APPLICATION_RATE_MM_PER_HR,
    DEFAULT_BORDER_TYPE,
    DEFAULT_ETO_SOURCE,
    DEFAULT_FORECAST_CREDIT_PCT,
    DEFAULT_IRRIGATION_EFFICIENCY_PCT,
    DEFAULT_MANUAL_ADJUSTMENT_PCT,
    DEFAULT_MAX_RUNTIME_MIN,
    DEFAULT_RAIN_EFFECTIVE_PCT,
    DEFAULT_ROLLUP_TIME,
    DEFAULT_SITE_NAME,
    DOMAIN,
    ETO_SOURCE_OPTIONS,
    SUBENTRY_TYPE_ZONE,
)

_LOGGER = logging.getLogger(__name__)


def _slugify(value: str) -> str:
    """Return a stable slug for a user-provided zone name."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return re.sub(r"_+", "_", slug)


class GardenHydroConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Garden Hydro config flow."""

    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls,
        config_entry: ConfigEntry,  # noqa: ARG003
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return supported config subentry flow handlers."""
        return {SUBENTRY_TYPE_ZONE: GardenHydroZoneSubentryFlow}

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._reconfigure_entry: config_entries.ConfigEntry | None = None

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

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of an existing config entry."""
        _LOGGER.debug("Entered async_step_reconfigure with input: %s", user_input)

        self._reconfigure_entry = self._get_reconfigure_entry()
        current_data = dict(self._reconfigure_entry.data)

        errors: dict[str, str] = {}
        if user_input is not None:
            site_name = str(user_input[CONF_SITE_NAME]).strip()
            if not site_name:
                errors[CONF_SITE_NAME] = "site_name_required"
            elif not user_input[CONF_ENABLE_HARGREAVES] and not user_input[CONF_ENABLE_PENMAN_MONTEITH]:
                errors["base"] = "at_least_one_engine_required"
            else:
                self._data = current_data
                self._data.update(user_input)
                self._data[CONF_SITE_NAME] = site_name
                self._data[CONF_LATITUDE] = self.hass.config.latitude
                self._data[CONF_ELEVATION] = self.hass.config.elevation
                return await self.async_step_reconfigure_weather_mapping()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SITE_NAME,
                        default=current_data.get(CONF_SITE_NAME, DEFAULT_SITE_NAME),
                    ): selector.TextSelector(),
                    vol.Required(
                        CONF_ROLLUP_TIME,
                        default=current_data.get(CONF_ROLLUP_TIME, DEFAULT_ROLLUP_TIME),
                    ): selector.TimeSelector(),
                    vol.Required(
                        CONF_ENABLE_HARGREAVES,
                        default=current_data.get(CONF_ENABLE_HARGREAVES, True),
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONF_ENABLE_PENMAN_MONTEITH,
                        default=current_data.get(CONF_ENABLE_PENMAN_MONTEITH, True),
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
                    vol.Required(CONF_FORECAST_RAIN_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Required(CONF_HUMIDITY_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Required(CONF_WIND_SPEED_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Required(CONF_SOLAR_RADIATION_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure_weather_mapping(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle weather mapping updates for an existing entry."""
        assert self._reconfigure_entry is not None  # noqa: S101

        current_data = dict(self._reconfigure_entry.data)
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = self._validate_weather_mapping(user_input)
            if not errors:
                self._data.update(user_input)
                self.hass.config_entries.async_update_entry(
                    self._reconfigure_entry,
                    data=self._data,
                    title=self._data[CONF_SITE_NAME],
                )
                await self.hass.config_entries.async_reload(self._reconfigure_entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure_weather_mapping",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TMIN_ENTITY_ID,
                        default=current_data.get(CONF_TMIN_ENTITY_ID),
                    ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                    vol.Required(
                        CONF_TMAX_ENTITY_ID,
                        default=current_data.get(CONF_TMAX_ENTITY_ID),
                    ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                    vol.Required(
                        CONF_RAIN_ENTITY_ID,
                        default=current_data.get(CONF_RAIN_ENTITY_ID),
                    ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                    vol.Required(
                        CONF_FORECAST_RAIN_ENTITY_ID,
                        default=current_data.get(CONF_FORECAST_RAIN_ENTITY_ID),
                    ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                    vol.Required(
                        CONF_HUMIDITY_ENTITY_ID,
                        default=current_data.get(CONF_HUMIDITY_ENTITY_ID),
                    ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                    vol.Required(
                        CONF_WIND_SPEED_ENTITY_ID,
                        default=current_data.get(CONF_WIND_SPEED_ENTITY_ID),
                    ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                    vol.Required(
                        CONF_SOLAR_RADIATION_ENTITY_ID,
                        default=current_data.get(CONF_SOLAR_RADIATION_ENTITY_ID),
                    ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
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


class GardenHydroZoneSubentryFlow(ConfigSubentryFlow):
    """Handle config subentries for watering zones."""

    def __init__(self) -> None:
        """Initialize the zone subentry flow."""
        self._zone_data: dict[str, Any] = {}

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Handle creating a watering zone subentry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            zone_name = str(user_input[CONF_ZONE_NAME]).strip()
            zone_slug = _slugify(zone_name)

            if not zone_name or not zone_slug:
                errors[CONF_ZONE_NAME] = "zone_name_required"
            elif self._zone_slug_exists(zone_slug):
                errors[CONF_ZONE_NAME] = "zone_already_exists"
            else:
                border_type = user_input[CONF_BORDER_TYPE]
                self._zone_data = {
                    CONF_ZONE_NAME: zone_name,
                    CONF_ZONE_SLUG: zone_slug,
                    CONF_ZONE_ENABLED: user_input[CONF_ZONE_ENABLED],
                    CONF_ETO_SOURCE: user_input[CONF_ETO_SOURCE],
                    CONF_BORDER_TYPE: border_type,
                    CONF_BORDER_FACTOR: BORDER_TYPE_FACTORS[border_type],
                    CONF_APPLICATION_RATE_MM_PER_HR: user_input[CONF_APPLICATION_RATE_MM_PER_HR],
                    CONF_MAX_RUNTIME_MIN: user_input[CONF_MAX_RUNTIME_MIN],
                    CONF_RAIN_EFFECTIVE_PCT: user_input[CONF_RAIN_EFFECTIVE_PCT],
                    CONF_FORECAST_CREDIT_PCT: user_input[CONF_FORECAST_CREDIT_PCT],
                    CONF_IRRIGATION_EFFICIENCY_PCT: user_input[CONF_IRRIGATION_EFFICIENCY_PCT],
                    CONF_MANUAL_ADJUSTMENT_PCT: user_input[CONF_MANUAL_ADJUSTMENT_PCT],
                }
                result = self.async_create_entry(
                    title=zone_name,
                    data=self._zone_data,
                )
                await self.hass.config_entries.async_reload(self._get_entry().entry_id)
                return result

        return self.async_show_form(
            step_id="user",
            data_schema=self._zone_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Handle reconfiguring a watering zone subentry."""
        subentry = self._get_reconfigure_subentry()
        current = dict(subentry.data)
        errors: dict[str, str] = {}

        if user_input is not None:
            zone_name = str(user_input[CONF_ZONE_NAME]).strip()
            zone_slug = current[CONF_ZONE_SLUG]
            if not zone_name:
                errors[CONF_ZONE_NAME] = "zone_name_required"
            else:
                border_type = user_input[CONF_BORDER_TYPE]
                data = current | {
                    CONF_ZONE_NAME: zone_name,
                    CONF_ZONE_ENABLED: user_input[CONF_ZONE_ENABLED],
                    CONF_ETO_SOURCE: user_input[CONF_ETO_SOURCE],
                    CONF_BORDER_TYPE: border_type,
                    CONF_BORDER_FACTOR: BORDER_TYPE_FACTORS[border_type],
                    CONF_APPLICATION_RATE_MM_PER_HR: user_input[CONF_APPLICATION_RATE_MM_PER_HR],
                    CONF_MAX_RUNTIME_MIN: user_input[CONF_MAX_RUNTIME_MIN],
                    CONF_RAIN_EFFECTIVE_PCT: user_input[CONF_RAIN_EFFECTIVE_PCT],
                    CONF_FORECAST_CREDIT_PCT: user_input[CONF_FORECAST_CREDIT_PCT],
                    CONF_IRRIGATION_EFFICIENCY_PCT: user_input[CONF_IRRIGATION_EFFICIENCY_PCT],
                    CONF_MANUAL_ADJUSTMENT_PCT: user_input[CONF_MANUAL_ADJUSTMENT_PCT],
                    CONF_ZONE_SLUG: zone_slug,
                }
                return self.async_update_reload_and_abort(
                    self._get_entry(),
                    subentry=subentry,
                    data=data,
                    title=zone_name,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._zone_schema(current),
            errors=errors,
        )

    def _zone_schema(self, current: dict[str, Any] | None = None) -> vol.Schema:
        """Return the schema for creating or editing a watering zone."""
        current = current or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_ZONE_NAME,
                    default=current.get(CONF_ZONE_NAME, "Front Border"),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_ZONE_ENABLED,
                    default=current.get(CONF_ZONE_ENABLED, True),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_ETO_SOURCE,
                    default=current.get(CONF_ETO_SOURCE, DEFAULT_ETO_SOURCE),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(ETO_SOURCE_OPTIONS),
                        translation_key=CONF_ETO_SOURCE,
                    )
                ),
                vol.Required(
                    CONF_BORDER_TYPE,
                    default=current.get(CONF_BORDER_TYPE, DEFAULT_BORDER_TYPE),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(BORDER_TYPE_OPTIONS),
                        translation_key=CONF_BORDER_TYPE,
                    )
                ),
                vol.Required(
                    CONF_APPLICATION_RATE_MM_PER_HR,
                    default=current.get(
                        CONF_APPLICATION_RATE_MM_PER_HR,
                        DEFAULT_APPLICATION_RATE_MM_PER_HR,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=100.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="mm/h",
                    )
                ),
                vol.Required(
                    CONF_MAX_RUNTIME_MIN,
                    default=current.get(CONF_MAX_RUNTIME_MIN, DEFAULT_MAX_RUNTIME_MIN),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=240,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="min",
                    )
                ),
                vol.Required(
                    CONF_RAIN_EFFECTIVE_PCT,
                    default=current.get(
                        CONF_RAIN_EFFECTIVE_PCT,
                        DEFAULT_RAIN_EFFECTIVE_PCT,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=100,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="%",
                    )
                ),
                vol.Required(
                    CONF_FORECAST_CREDIT_PCT,
                    default=current.get(
                        CONF_FORECAST_CREDIT_PCT,
                        DEFAULT_FORECAST_CREDIT_PCT,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=100,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="%",
                    )
                ),
                vol.Required(
                    CONF_IRRIGATION_EFFICIENCY_PCT,
                    default=current.get(
                        CONF_IRRIGATION_EFFICIENCY_PCT,
                        DEFAULT_IRRIGATION_EFFICIENCY_PCT,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=100,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="%",
                    )
                ),
                vol.Required(
                    CONF_MANUAL_ADJUSTMENT_PCT,
                    default=current.get(
                        CONF_MANUAL_ADJUSTMENT_PCT,
                        DEFAULT_MANUAL_ADJUSTMENT_PCT,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-100,
                        max=100,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="%",
                    )
                ),
            }
        )

    def _zone_slug_exists(self, zone_slug: str) -> bool:
        """Return True if a zone slug already exists for the parent entry."""
        entry = self._get_entry()
        return any(
            subentry.subentry_type == SUBENTRY_TYPE_ZONE and subentry.data.get(CONF_ZONE_SLUG) == zone_slug
            for subentry in entry.subentries.values()
        )
