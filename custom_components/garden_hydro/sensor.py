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

from .const import DOMAIN, NAME, UNIT_MILLIMETERS, UNIT_MJ_M2_DAY
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
        key="eto_hargreaves_mm",
        translation_key="eto_hargreaves_mm",
        native_unit_of_measurement=UNIT_MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda result: result.eto_hargreaves_mm,
        round_digits=2,
    ),
    GardenHydroSensorDescription(
        key="eto_penman_monteith_mm",
        translation_key="eto_penman_monteith_mm",
        native_unit_of_measurement=UNIT_MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda result: result.eto_penman_monteith_mm,
        round_digits=2,
    ),
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
        value_fn=lambda result: result.calc_mode,
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
        key="rh_mean_pct",
        translation_key="rh_mean_pct",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.humidity_pct,
        round_digits=1,
    ),
    GardenHydroSensorDescription(
        key="wind_speed_m_s",
        translation_key="wind_speed_m_s",
        native_unit_of_measurement="m/s",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.wind_speed_m_s,
        round_digits=1,
    ),
    GardenHydroSensorDescription(
        key="solar_radiation_mj_m2_day",
        translation_key="solar_radiation_mj_m2_day",
        native_unit_of_measurement="MJ/m²/day",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.solar_radiation_mj_m2_day,
        round_digits=1,
    ),
    GardenHydroSensorDescription(
        key="latitude",
        translation_key="latitude",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.latitude,
        round_digits=4,
    ),
    GardenHydroSensorDescription(
        key="elevation_m",
        translation_key="elevation_m",
        native_unit_of_measurement="m",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.elevation_m,
        round_digits=1,
    ),
    GardenHydroSensorDescription(
        key="hargreaves_status",
        translation_key="hargreaves_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.hargreaves_status,
    ),
    GardenHydroSensorDescription(
        key="penman_monteith_status",
        translation_key="penman_monteith_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda result: result.penman_monteith_status,
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
                "alias_for": "eto_hargreaves_mm",
                "eto_hargreaves_mm": result.eto_hargreaves_mm,
                "eto_penman_monteith_mm": result.eto_penman_monteith_mm,
                "tmin_c": result.tmin_c,
                "tmax_c": result.tmax_c,
                "tmean_c": result.tmean_c,
                "temperature_delta_c": result.temperature_delta_c,
                "humidity_pct": result.humidity_pct,
                "wind_speed_m_s": result.wind_speed_m_s,
                "solar_radiation_mj_m2_day": result.solar_radiation_mj_m2_day,
                "latitude": result.latitude,
                "elevation_m": result.elevation_m,
                "ra_mj_m2_day": result.ra_used_mj_m2_day,
                "hargreaves_status": result.hargreaves_status,
                "penman_monteith_status": result.penman_monteith_status,
                "weather_status": result.weather_status,
                "source_tmin_entity_id": result.source_tmin_entity_id,
                "source_tmax_entity_id": result.source_tmax_entity_id,
                "source_rain_entity_id": result.source_rain_entity_id,
                "source_forecast_rain_entity_id": result.source_forecast_rain_entity_id,
                "calculation_date": result.calculation_date,
                "calc_mode": result.calc_mode,
            }.items()
            if value is not None
        }
