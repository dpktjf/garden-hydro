"""Switch entities for Garden Hydro watering zones."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GardenHydroCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from custom_components.garden_hydro import GardenHydroEntryData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Garden Hydro zone switch entities."""
    entry_data: GardenHydroEntryData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GardenHydroZoneEnabledSwitch(
            entry_data.coordinator,
            entry,
            zone_slug,
            settings.zone_name,
        )
        for zone_slug, settings in entry_data.runtime.zone_settings.items()
    )


class GardenHydroZoneEnabledSwitch(
    CoordinatorEntity[GardenHydroCoordinator],
    SwitchEntity,
):
    """Enable or disable advisory calculation for one watering zone."""

    _attr_has_entity_name = True
    _attr_translation_key = "zone_enabled"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: GardenHydroCoordinator,
        entry: ConfigEntry,
        zone_slug: str,
        zone_name: str,
    ) -> None:
        """Initialize the zone enabled switch."""
        super().__init__(coordinator)
        self._zone_slug = zone_slug
        self._attr_unique_id = f"{entry.entry_id}:zone:{zone_slug}:enabled"
        self._attr_name = "Enabled"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}:{zone_slug}")},
            name=zone_name,
            manufacturer="DPK",
            model="Garden Hydro Zone",
            via_device=(DOMAIN, entry.entry_id),
        )

    @property
    def is_on(self) -> bool:
        """Return True if the zone is enabled."""
        return self.coordinator.runtime.zone_settings[self._zone_slug].enabled

    async def async_turn_on(self, **kwargs: object) -> None:  # noqa: ARG002
        """Enable this watering zone."""
        self.coordinator.runtime.zone_settings[self._zone_slug].enabled = True
        self.async_write_ha_state()
        await self.coordinator.async_run_rollup(is_scheduled=False)

    async def async_turn_off(self, **kwargs: object) -> None:  # noqa: ARG002
        """Disable this watering zone."""
        self.coordinator.runtime.zone_settings[self._zone_slug].enabled = False
        self.async_write_ha_state()
        await self.coordinator.async_run_rollup(is_scheduled=False)
