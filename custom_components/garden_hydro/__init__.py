"""The Garden Hydro integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ENTRY_ID,
    CALC_MODE,
    DOMAIN,
    PLATFORMS,
    RA_DEFAULTS,
    SERVICE_RECALCULATE_SITE,
)
from .coordinator import GardenHydroCoordinator
from .models import RuntimeData, SiteCalculationResult

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall

SERVICE_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY_ID): cv.string})


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
