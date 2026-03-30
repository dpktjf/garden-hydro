"""Sensor entities for Garden Hydro."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CALC_MODE, DOMAIN, NAME, UNIT_MILLIMETERS, UNIT_MJ_M2_DAY
from .coordinator import GardenHydroCoordinator

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from custom_components.garden_hydro import GardenHydroEntryData

    from .models import SiteCalculationResult


@dataclass(frozen=True, kw_only=True)
class GardenHydroSensorDescription(SensorEntityDescription):
    """Describe a coordinator-backed Garden Hydro sensor."""

    value_fn: Callable[[SiteCalculationResult], Any]
    round_digits: int | None = None


SENSOR_DESCRIPTIONS: tuple[GardenHydroSensorDescription, ...] = (
    GardenHydroSensorDescription(
        key="daily_eto_mm",
        translation_key="daily_eto_mm",
        native_unit_of_measurement=UNIT_MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda result: result.daily_eto_mm,
        round_digits=2,
    ),
    GardenHydroSensorDescription(
        key="daily_rain_mm",
        translation_key="daily_rain_mm",
        native_unit_of_measurement=UNIT_MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda result: result.daily_rain_mm,
        round_digits=2,
    ),
    GardenHydroSensorDescription(
        key="forecast_rain_mm",
        translation_key="forecast_rain_mm",
        native_unit_of_measurement=UNIT_MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda result: result.forecast_rain_mm,
        round_digits=2,
    ),
    GardenHydroSensorDescription(
        key="last_rollup",
        translation_key="last_rollup",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda result: result.last_rollup,
    ),
    GardenHydroSensorDescription(
        key="last_calculation",
        translation_key="last_calculation",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda result: result.last_calculation,
    ),
    GardenHydroSensorDescription(
        key="calc_mode",
        translation_key="calc_mode",
        value_fn=lambda result: result.calc_mode or CALC_MODE,
    ),
    GardenHydroSensorDescription(
        key="tmin_c",
        translation_key="tmin_c",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.tmin_c,
        round_digits=1,
    ),
    GardenHydroSensorDescription(
        key="tmax_c",
        translation_key="tmax_c",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.tmax_c,
        round_digits=1,
    ),
    GardenHydroSensorDescription(
        key="ra_used_mj_m2_day",
        translation_key="ra_used_mj_m2_day",
        native_unit_of_measurement=UNIT_MJ_M2_DAY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.ra_used_mj_m2_day,
        round_digits=1,
    ),
    GardenHydroSensorDescription(
        key="weather_status",
        translation_key="weather_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.weather_status,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Garden Hydro sensor entities for a config entry."""
    entry_data: GardenHydroEntryData = hass.data[DOMAIN][entry.entry_id]
    coordinator: GardenHydroCoordinator = entry_data.coordinator
    async_add_entities(GardenHydroSensor(coordinator, entry, description) for description in SENSOR_DESCRIPTIONS)


class GardenHydroSensor(CoordinatorEntity[GardenHydroCoordinator], RestoreSensor):
    """Coordinator-backed sensor with restore support."""

    _attr_has_entity_name = True
    entity_description: GardenHydroSensorDescription

    def __init__(
        self,
        coordinator: GardenHydroCoordinator,
        entry: ConfigEntry,
        description: GardenHydroSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}:site:{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="DPK",
            model="Garden Hydro Site",
        )
        self._attr_entity_category = description.entity_category
        self._attr_translation_key = description.translation_key
        self._attr_suggested_display_precision = description.round_digits
        self._restored_native_value: Any = None
        self._restored_unit: str | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the previous state after Home Assistant starts."""
        await super().async_added_to_hass()
        last_data = await self.async_get_last_sensor_data()
        if last_data is None:
            return

        self._restored_native_value = last_data.native_value
        self._restored_unit = last_data.native_unit_of_measurement

    @property
    def native_value(self) -> Any:
        """Return the current native value for the sensor."""
        value = self.entity_description.value_fn(self.coordinator.data)
        if value is None:
            return self._restored_native_value

        if isinstance(value, float) and self.entity_description.round_digits is not None:
            return round(value, self.entity_description.round_digits)

        return value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the native unit, falling back to restored state if needed."""
        if self.entity_description.native_unit_of_measurement is not None:
            return self.entity_description.native_unit_of_measurement

        return self._restored_unit

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose calculation context for the main daily ETo sensor."""
        if self.entity_description.key != "daily_eto_mm":
            return None

        result = self.coordinator.data

        return {
            key: value
            for key, value in {
                "tmin_c": result.tmin_c,
                "tmax_c": result.tmax_c,
                "tmean_c": result.tmean_c,
                "temperature_delta_c": result.temperature_delta_c,
                "ra_mj_m2_day": result.ra_used_mj_m2_day,
                "source_tmin_entity_id": result.source_tmin_entity_id,
                "source_tmax_entity_id": result.source_tmax_entity_id,
                "calculation_date": result.calculation_date,
                "calc_mode": result.calc_mode,
            }.items()
            if value is not None
        }
