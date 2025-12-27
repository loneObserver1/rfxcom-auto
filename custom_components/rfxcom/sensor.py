"""Support des capteurs RFXCOM (température, humidité)."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    PROTOCOL_TEMP_HUM,
    CONF_PROTOCOL,
    CONF_DEVICE_ID,
)
from .coordinator import RFXCOMCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure les capteurs RFXCOM."""
    coordinator: RFXCOMCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Charger les appareils configurés
    devices = entry.options.get("devices", [])
    _LOGGER.debug("Configuration de %s appareils RFXCOM (sensors)", len(devices))

    entities = []
    for device_config in devices:
        if device_config.get(CONF_PROTOCOL) == PROTOCOL_TEMP_HUM:
            device_id = device_config.get(CONF_DEVICE_ID)
            sensor_data = device_config.get("sensor_data", {})
            name = device_config.get("name", f"RFXCOM Temp/Hum {device_id}")
            unique_id = f"{entry.entry_id}_temp_hum_{device_id}"

            _LOGGER.debug(
                "Création capteur TEMP_HUM: %s (device_id=%s)",
                name,
                device_id,
            )

            # Créer les entités température et humidité
            entities.append(
                RFXCOMTemperatureSensor(
                    coordinator=coordinator,
                    name=f"{name} Temperature",
                    device_id=device_id,
                    unique_id=f"{unique_id}_temp",
                )
            )
            entities.append(
                RFXCOMHumiditySensor(
                    coordinator=coordinator,
                    name=f"{name} Humidity",
                    device_id=device_id,
                    unique_id=f"{unique_id}_hum",
                )
            )

    _LOGGER.info("Création de %s entités sensor RFXCOM", len(entities))
    async_add_entities(entities)


class RFXCOMTemperatureSensor(
    CoordinatorEntity[RFXCOMCoordinator], SensorEntity
):
    """Représente un capteur de température RFXCOM."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: RFXCOMCoordinator,
        name: str,
        device_id: str,
        unique_id: str,
    ) -> None:
        """Initialise le capteur de température."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._device_id = device_id
        self._native_value: float | None = None

    @property
    def native_value(self) -> float | None:
        """Retourne la valeur de température."""
        # Récupérer la valeur depuis les appareils découverts
        discovered = self.coordinator.get_discovered_devices()
        for device in discovered:
            if (
                device.get(CONF_PROTOCOL) == PROTOCOL_TEMP_HUM
                and device.get(CONF_DEVICE_ID) == self._device_id
            ):
                temp = device.get("temperature")
                if temp is not None:
                    if self._native_value != temp:
                        _LOGGER.debug(
                            "Température mise à jour: %s = %.1f°C (était %.1f°C)",
                            self._attr_name,
                            temp,
                            self._native_value,
                        )
                    self._native_value = temp
                break

        return self._native_value


class RFXCOMHumiditySensor(
    CoordinatorEntity[RFXCOMCoordinator], SensorEntity
):
    """Représente un capteur d'humidité RFXCOM."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: RFXCOMCoordinator,
        name: str,
        device_id: str,
        unique_id: str,
    ) -> None:
        """Initialise le capteur d'humidité."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._device_id = device_id
        self._native_value: int | None = None

    @property
    def native_value(self) -> int | None:
        """Retourne la valeur d'humidité."""
        # Récupérer la valeur depuis les appareils découverts
        discovered = self.coordinator.get_discovered_devices()
        for device in discovered:
            if (
                device.get(CONF_PROTOCOL) == PROTOCOL_TEMP_HUM
                and device.get(CONF_DEVICE_ID) == self._device_id
            ):
                hum = device.get("humidity")
                if hum is not None:
                    hum_int = int(hum)
                    if self._native_value != hum_int:
                        _LOGGER.debug(
                            "Humidité mise à jour: %s = %s%% (était %s%%)",
                            self._attr_name,
                            hum_int,
                            self._native_value,
                        )
                    self._native_value = hum_int
                break

        return self._native_value

