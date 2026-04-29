"""The Garden Hydro integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ENTRY_ID,
    CALC_MODE,
    CONF_APPLICATION_RATE_MM_PER_HR,
    CONF_BORDER_FACTOR,
    CONF_BORDER_TYPE,
    CONF_ETO_SOURCE,
    CONF_FORECAST_CREDIT_PCT,
    CONF_IRRIGATION_EFFICIENCY_PCT,
    CONF_MANUAL_ADJUSTMENT_PCT,
    CONF_MAX_RUNTIME_MIN,
    CONF_RAIN_EFFECTIVE_PCT,
    CONF_ZONE_ENABLED,
    CONF_ZONE_NAME,
    CONF_ZONE_SLUG,
    DOMAIN,
    PLATFORMS,
    RA_DEFAULTS,
    SERVICE_RECALCULATE_SITE,
    SUBENTRY_TYPE_ZONE,
)
from .coordinator import GardenHydroCoordinator
from .models import RuntimeData, SiteCalculationResult, ZoneSettings

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall

SERVICE_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY_ID): cv.string})

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class GardenHydroEntryData:
    """Runtime objects stored for a loaded config entry."""

    entry: ConfigEntry
    runtime: RuntimeData
    coordinator: GardenHydroCoordinator


async def async_setup(hass: HomeAssistant, config: Mapping[str, Any]) -> bool:  # noqa: ARG001
    """Set up the integration domain and register services."""
    hass.data.setdefault(DOMAIN, {})

    async def _handle_recalculate_site(call: ServiceCall) -> None:
        """Recalculate one or more loaded site entries on demand."""
        _LOGGER.warning("garden_hydro.recalculate_site called")
        requested_entry_id: str | None = call.data.get(ATTR_ENTRY_ID)
        targets: list[GardenHydroCoordinator] = []

        for entry_id, entry_data in hass.data[DOMAIN].items():
            if requested_entry_id and entry_id != requested_entry_id:
                continue
            targets.append(entry_data.coordinator)

        for coordinator in targets:
            await coordinator.async_run_rollup(is_scheduled=False)

    if not hass.services.has_service(DOMAIN, SERVICE_RECALCULATE_SITE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RECALCULATE_SITE,
            _handle_recalculate_site,
            schema=SERVICE_SCHEMA,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Garden Hydro from a config entry."""
    runtime = RuntimeData(
        ra_values=RA_DEFAULTS.copy(),
        result=SiteCalculationResult(calc_mode=CALC_MODE),
        zone_settings=_zone_settings_from_subentries(entry),
    )
    coordinator = GardenHydroCoordinator(
        hass,
        entry.entry_id,
        runtime,
        dict(entry.data),
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = GardenHydroEntryData(
        entry=entry,
        runtime=runtime,
        coordinator=coordinator,
    )

    await coordinator.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _zone_settings_from_subentries(entry: ConfigEntry) -> dict[str, ZoneSettings]:
    """Return watering zone settings from config subentries."""
    zones: dict[str, ZoneSettings] = {}
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_ZONE:
            continue

        data = subentry.data
        zone_slug = str(data[CONF_ZONE_SLUG])
        zones[zone_slug] = ZoneSettings(
            zone_name=str(data[CONF_ZONE_NAME]),
            zone_slug=zone_slug,
            enabled=bool(data[CONF_ZONE_ENABLED]),
            eto_source=str(data[CONF_ETO_SOURCE]),
            border_type=str(data[CONF_BORDER_TYPE]),
            border_factor=float(data[CONF_BORDER_FACTOR]),
            application_rate_mm_per_hr=float(data[CONF_APPLICATION_RATE_MM_PER_HR]),
            max_runtime_min=float(data[CONF_MAX_RUNTIME_MIN]),
            rain_effective_pct=float(data[CONF_RAIN_EFFECTIVE_PCT]),
            forecast_credit_pct=float(data[CONF_FORECAST_CREDIT_PCT]),
            irrigation_efficiency_pct=float(data[CONF_IRRIGATION_EFFICIENCY_PCT]),
            manual_adjustment_pct=float(data[CONF_MANUAL_ADJUSTMENT_PCT]),
        )
    return zones


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Garden Hydro config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data: GardenHydroEntryData | None = hass.data[DOMAIN].pop(
            entry.entry_id,
            None,
        )
        if entry_data is not None:
            await entry_data.coordinator.async_stop()

    return unload_ok
