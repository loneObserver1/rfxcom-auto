"""Support des interrupteurs RFXCOM."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    PROTOCOL_AC,
    PROTOCOL_ARC,
    CMD_ON,
    CMD_OFF,
    CONF_PROTOCOL,
    CONF_DEVICE_ID,
    CONF_HOUSE_CODE,
    CONF_UNIT_CODE,
)
from .coordinator import RFXCOMCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure les interrupteurs RFXCOM."""
    coordinator: RFXCOMCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Charger les appareils configurés
    devices = entry.options.get("devices", [])
    
    entities = []
    for device_config in devices:
        entity = RFXCOMSwitch(
            coordinator=coordinator,
            name=device_config["name"],
            protocol=device_config[CONF_PROTOCOL],
            device_id=device_config.get(CONF_DEVICE_ID),
            house_code=device_config.get(CONF_HOUSE_CODE),
            unit_code=device_config.get(CONF_UNIT_CODE),
            unique_id=f"{entry.entry_id}_{device_config.get(CONF_DEVICE_ID, device_config.get(CONF_HOUSE_CODE, ''))}_{device_config.get(CONF_UNIT_CODE, '')}",
        )
        entities.append(entity)

    async_add_entities(entities)


class RFXCOMSwitch(
    CoordinatorEntity[RFXCOMCoordinator], SwitchEntity, RestoreEntity
):
    """Représente un interrupteur RFXCOM."""

    def __init__(
        self,
        coordinator: RFXCOMCoordinator,
        name: str,
        protocol: str,
        device_id: str | None = None,
        house_code: str | None = None,
        unit_code: str | None = None,
        unique_id: str | None = None,
    ) -> None:
        """Initialise l'interrupteur RFXCOM."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._protocol = protocol
        self._device_id = device_id
        self._house_code = house_code
        self._unit_code = unit_code
        self._is_on = False

    async def async_added_to_hass(self) -> None:
        """Appelé lorsque l'entité est ajoutée à Home Assistant."""
        await super().async_added_to_hass()
        
        # Restaurer l'état précédent
        if (last_state := await self.async_get_last_state()) is not None:
            self._is_on = last_state.state == "on"

    @property
    def is_on(self) -> bool:
        """Retourne l'état de l'interrupteur."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Allume l'interrupteur."""
        success = await self.coordinator.send_command(
            protocol=self._protocol,
            device_id=self._device_id or "",
            command=CMD_ON,
            house_code=self._house_code,
            unit_code=self._unit_code,
        )
        
        if success:
            self._is_on = True
            self.async_write_ha_state()
        else:
            _LOGGER.error("Échec de l'envoi de la commande ON")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Éteint l'interrupteur."""
        success = await self.coordinator.send_command(
            protocol=self._protocol,
            device_id=self._device_id or "",
            command=CMD_OFF,
            house_code=self._house_code,
            unit_code=self._unit_code,
        )
        
        if success:
            self._is_on = False
            self.async_write_ha_state()
        else:
            _LOGGER.error("Échec de l'envoi de la commande OFF")

