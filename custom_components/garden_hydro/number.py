"""Number entities for Garden Hydro."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntityDescription, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, MONTH_KEYS, NAME, RA_DEFAULTS, UNIT_MJ_M2_DAY
from .models import RuntimeData


@dataclass(frozen=True, kw_only=True)
class GardenHydroNumberDescription(NumberEntityDescription):
    """Describe a Garden Hydro number entity."""


NUMBER_DESCRIPTIONS: tuple[GardenHydroNumberDescription, ...] = tuple(
    GardenHydroNumberDescription(
        key=f"ra_{month}",
        translation_key=f"ra_{month}",
        native_min_value=0.0,
        native_max_value=60.0,
        native_step=0.1,
        native_unit_of_measurement=UNIT_MJ_M2_DAY,
        entity_category=EntityCategory.CONFIG,
    )
    for month in MONTH_KEYS
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the site-level Ra number entities."""
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]["runtime"]
    async_add_entities(
        GardenHydroRaNumber(entry, runtime, description)
        for description in NUMBER_DESCRIPTIONS
    )


class GardenHydroRaNumber(RestoreNumber):
    """Editable monthly extraterrestrial radiation value."""

    _attr_has_entity_name = True
    entity_description: GardenHydroNumberDescription

    def __init__(
        self,
        entry: ConfigEntry,
        runtime: RuntimeData,
        description: GardenHydroNumberDescription,
    ) -> None:
        """Initialize the monthly Ra number entity."""
        self._entry = entry
        self._runtime = runtime
        self.entity_description = description
        self._month_key = description.key.removeprefix("ra_")
        self._attr_unique_id = f"{entry.entry_id}:site:{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="DPK",
            model="Garden Hydro Site",
        )
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_translation_key = description.translation_key
        self._attr_suggested_display_precision = 1
        self._attr_mode = "box"
        self._attr_native_value = runtime.ra_values.get(
            self._month_key,
            RA_DEFAULTS[self._month_key],
        )

    async def async_added_to_hass(self) -> None:
        """Restore the previous value after Home Assistant starts."""
        await super().async_added_to_hass()
        last_data = await self.async_get_last_number_data()
        if last_data is None or last_data.native_value is None:
            return

        restored_value = round(float(last_data.native_value), 1)
        self._attr_native_value = restored_value
        self._runtime.ra_values[self._month_key] = restored_value

    async def async_set_native_value(self, value: float) -> None:
        """Persist a new monthly Ra value."""
        native_value = round(float(value), 1)
        self._attr_native_value = native_value
        self._runtime.ra_values[self._month_key] = native_value
        self.async_write_ha_state()
