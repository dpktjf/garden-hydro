"""Select entities for Garden Hydro watering zones."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BORDER_TYPE_FACTORS,
    BORDER_TYPE_OPTIONS,
    DOMAIN,
    ETO_SOURCE_OPTIONS,
)
from .coordinator import GardenHydroCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from custom_components.garden_hydro import GardenHydroEntryData


@dataclass(frozen=True, kw_only=True)
class GardenHydroZoneSelectDescription(SelectEntityDescription):
    """Describe a Garden Hydro zone select."""

    fallback_name: str


ZONE_SELECT_DESCRIPTIONS = (
    GardenHydroZoneSelectDescription(
        key="eto_source",
        translation_key="zone_eto_source",
        fallback_name="ETo source",
        options=list(ETO_SOURCE_OPTIONS),
        entity_category=EntityCategory.CONFIG,
    ),
    GardenHydroZoneSelectDescription(
        key="border_type",
        translation_key="zone_border_type",
        fallback_name="Border type",
        options=list(BORDER_TYPE_OPTIONS),
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Garden Hydro zone select entities."""
    entry_data: GardenHydroEntryData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GardenHydroZoneSelect(
            entry_data.coordinator,
            entry,
            zone_slug,
            settings.zone_name,
            description,
        )
        for zone_slug, settings in entry_data.runtime.zone_settings.items()
        for description in ZONE_SELECT_DESCRIPTIONS
    )


class GardenHydroZoneSelect(CoordinatorEntity[GardenHydroCoordinator], SelectEntity):
    """Select entity for one Garden Hydro zone setting."""

    _attr_has_entity_name = True
    entity_description: GardenHydroZoneSelectDescription

    def __init__(
        self,
        coordinator: GardenHydroCoordinator,
        entry: ConfigEntry,
        zone_slug: str,
        zone_name: str,
        description: GardenHydroZoneSelectDescription,
    ) -> None:
        """Initialize the zone select."""
        super().__init__(coordinator)
        self.entity_description = description
        self._zone_slug = zone_slug
        self._attr_unique_id = f"{entry.entry_id}:zone:{zone_slug}:{description.key}"
        self._attr_translation_key = description.translation_key
        self._attr_name = description.fallback_name
        self._attr_entity_category = description.entity_category
        self._attr_options = list(description.options or [])
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}:{zone_slug}")},
            name=zone_name,
            manufacturer="DPK",
            model="Garden Hydro Zone",
            via_device=(DOMAIN, entry.entry_id),
        )

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        settings = self.coordinator.runtime.zone_settings[self._zone_slug]
        return getattr(settings, self.entity_description.key)

    async def async_select_option(self, option: str) -> None:
        """Select a new option and recalculate advisory output."""
        if option not in (self.options or []):
            return
        settings = self.coordinator.runtime.zone_settings[self._zone_slug]
        setattr(settings, self.entity_description.key, option)
        if self.entity_description.key == "border_type":
            settings.border_factor = BORDER_TYPE_FACTORS[option]
        self.async_write_ha_state()
        await self.coordinator.async_run_rollup(is_scheduled=False)
