"""Number entities for Garden Hydro."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode, RestoreNumber
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    CONF_APPLICATION_RATE_MM_PER_HR,
    CONF_BORDER_FACTOR,
    CONF_FORECAST_CREDIT_PCT,
    CONF_IRRIGATION_EFFICIENCY_PCT,
    CONF_MANUAL_ADJUSTMENT_PCT,
    CONF_MAX_RUNTIME_MIN,
    CONF_RAIN_EFFECTIVE_PCT,
    DOMAIN,
    MONTH_KEYS,
    NAME,
    RA_DEFAULTS,
    UNIT_MILLIMETERS,
    UNIT_MJ_M2_DAY,
    UNIT_PERCENT,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from custom_components.garden_hydro import GardenHydroEntryData

    from .coordinator import GardenHydroCoordinator
    from .models import RuntimeData


@dataclass(frozen=True, kw_only=True)
class GardenHydroNumberDescription(NumberEntityDescription):
    """Describe a Garden Hydro number entity."""

    fallback_name: str | None = None


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

ZONE_NUMBER_DESCRIPTIONS: tuple[GardenHydroNumberDescription, ...] = (
    GardenHydroNumberDescription(
        key=CONF_BORDER_FACTOR,
        translation_key="zone_border_factor",
        fallback_name="Border factor",
        native_min_value=0.1,
        native_max_value=2.0,
        native_step=0.05,
        entity_category=EntityCategory.CONFIG,
    ),
    GardenHydroNumberDescription(
        key=CONF_APPLICATION_RATE_MM_PER_HR,
        translation_key="zone_application_rate_mm_per_hr",
        fallback_name="Application rate",
        native_min_value=0.1,
        native_max_value=100.0,
        native_step=0.1,
        native_unit_of_measurement=f"{UNIT_MILLIMETERS}/h",
        entity_category=EntityCategory.CONFIG,
    ),
    GardenHydroNumberDescription(
        key=CONF_MAX_RUNTIME_MIN,
        translation_key="zone_max_runtime_min",
        fallback_name="Maximum runtime",
        native_min_value=1.0,
        native_max_value=240.0,
        native_step=1.0,
        native_unit_of_measurement="min",
        entity_category=EntityCategory.CONFIG,
    ),
    GardenHydroNumberDescription(
        key=CONF_RAIN_EFFECTIVE_PCT,
        translation_key="zone_rain_effective_pct",
        fallback_name="Rain effectiveness",
        native_min_value=0.0,
        native_max_value=100.0,
        native_step=1.0,
        native_unit_of_measurement=UNIT_PERCENT,
        entity_category=EntityCategory.CONFIG,
    ),
    GardenHydroNumberDescription(
        key=CONF_FORECAST_CREDIT_PCT,
        translation_key="zone_forecast_credit_pct",
        fallback_name="Forecast credit",
        native_min_value=0.0,
        native_max_value=100.0,
        native_step=1.0,
        native_unit_of_measurement=UNIT_PERCENT,
        entity_category=EntityCategory.CONFIG,
    ),
    GardenHydroNumberDescription(
        key=CONF_IRRIGATION_EFFICIENCY_PCT,
        translation_key="zone_irrigation_efficiency_pct",
        fallback_name="Irrigation efficiency",
        native_min_value=1.0,
        native_max_value=100.0,
        native_step=1.0,
        native_unit_of_measurement=UNIT_PERCENT,
        entity_category=EntityCategory.CONFIG,
    ),
    GardenHydroNumberDescription(
        key=CONF_MANUAL_ADJUSTMENT_PCT,
        translation_key="zone_manual_adjustment_pct",
        fallback_name="Manual adjustment",
        native_min_value=-100.0,
        native_max_value=100.0,
        native_step=1.0,
        native_unit_of_measurement=UNIT_PERCENT,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the site-level Ra number entities."""
    entry_data: GardenHydroEntryData = hass.data[DOMAIN][entry.entry_id]
    runtime: RuntimeData = entry_data.runtime
    entities: list[NumberEntity] = [
        GardenHydroRaNumber(entry, runtime, description) for description in NUMBER_DESCRIPTIONS
    ]
    for zone_slug, settings in runtime.zone_settings.items():
        entities.extend(
            GardenHydroZoneNumber(
                entry_data.coordinator,
                entry,
                zone_slug,
                settings.zone_name,
                description,
            )
            for description in ZONE_NUMBER_DESCRIPTIONS
        )
    async_add_entities(entities)


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
        self._attr_mode = NumberMode.BOX
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


class GardenHydroZoneNumber(RestoreNumber):
    """Editable numeric setting for a Garden Hydro watering zone."""

    _attr_has_entity_name = True
    entity_description: GardenHydroNumberDescription

    def __init__(
        self,
        coordinator: GardenHydroCoordinator,
        entry: ConfigEntry,
        zone_slug: str,
        zone_name: str,
        description: GardenHydroNumberDescription,
    ) -> None:
        """Initialize the zone number."""
        self.entity_description = description
        self._coordinator = coordinator
        self._zone_slug = zone_slug
        self._attr_unique_id = f"{entry.entry_id}:zone:{zone_slug}:{description.key}"
        self._attr_translation_key = description.translation_key
        self._attr_name = description.fallback_name
        self._attr_entity_category = description.entity_category
        self._attr_native_min_value = description.native_min_value or 0.0
        self._attr_native_max_value = description.native_max_value or 100.0
        self._attr_native_step = description.native_step or 1.0
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_mode = NumberMode.BOX
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}:{zone_slug}")},
            name=zone_name,
            manufacturer="DPK",
            model="Garden Hydro Zone",
            via_device=(DOMAIN, entry.entry_id),
        )

    @property
    def native_value(self) -> float:
        """Return the current numeric zone setting."""
        settings = self._coordinator.runtime.zone_settings[self._zone_slug]
        return float(getattr(settings, self.entity_description.key))

    async def async_set_native_value(self, value: float) -> None:
        """Set a numeric zone setting and recalculate advisory output."""
        settings = self._coordinator.runtime.zone_settings[self._zone_slug]
        setattr(settings, self.entity_description.key, float(value))
        self.async_write_ha_state()
        await self._coordinator.async_run_rollup(is_scheduled=False)
