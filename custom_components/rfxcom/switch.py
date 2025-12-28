"""Support des interrupteurs RFXCOM."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
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
    _LOGGER.debug("Configuration de %s appareils RFXCOM", len(devices))

    entities = []
    for idx, device_config in enumerate(devices):
        # Ne créer une entité switch que si le type n'est pas "cover"
        if device_config.get("device_type") == "cover":
            continue
            
        _LOGGER.debug(
            "Création entité %s: %s (protocol=%s)",
            idx + 1,
            device_config.get("name", "Sans nom"),
            device_config.get(CONF_PROTOCOL),
        )
        
        # Générer un unique_id unique en incluant l'index et le protocole
        protocol = device_config.get(CONF_PROTOCOL, "")
        device_id = device_config.get(CONF_DEVICE_ID)
        house_code = device_config.get(CONF_HOUSE_CODE)
        unit_code = device_config.get(CONF_UNIT_CODE)
        
        # Construire l'identifiant unique avec l'index pour garantir l'unicité
        if device_id:
            unique_id = f"{entry.entry_id}_{protocol}_{device_id}_{idx}"
            device_identifier = f"{protocol}_{device_id}"
        elif house_code and unit_code:
            unique_id = f"{entry.entry_id}_{protocol}_{house_code}_{unit_code}_{idx}"
            device_identifier = f"{protocol}_{house_code}_{unit_code}"
        else:
            # Fallback: utiliser le nom et l'index
            name_slug = device_config.get("name", "unknown").lower().replace(" ", "_")
            unique_id = f"{entry.entry_id}_{protocol}_{name_slug}_{idx}"
            device_identifier = f"{protocol}_{name_slug}"
        
        # Créer ou récupérer le device dans le device registry
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_identifier)},
            name=device_config.get("name", "Sans nom"),
            manufacturer="RFXCOM",
            model=protocol,
        )
        
        entity = RFXCOMSwitch(
            coordinator=coordinator,
            name=device_config["name"],
            protocol=protocol,
            device_id=device_id,
            house_code=house_code,
            unit_code=unit_code,
            unique_id=unique_id,
            device_info=DeviceInfo(
                identifiers={(DOMAIN, device_identifier)},
                name=device_config.get("name", "Sans nom"),
                manufacturer="RFXCOM",
                model=protocol,
            ),
        )
        entities.append(entity)

    _LOGGER.info("Création de %s entités switch RFXCOM", len(entities))
    async_add_entities(entities)


class RFXCOMSwitch(CoordinatorEntity[RFXCOMCoordinator], SwitchEntity):
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
        device_info: DeviceInfo | None = None,
    ) -> None:
        """Initialise l'interrupteur RFXCOM."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_device_info = device_info
        self._protocol = protocol
        self._device_id = device_id
        self._house_code = house_code
        self._unit_code = unit_code
        self._is_on = False

    async def async_added_to_hass(self) -> None:
        """Appelé lorsque l'entité est ajoutée à Home Assistant."""
        await super().async_added_to_hass()

        # Note: La restauration de l'état n'est pas implémentée car les switches RFXCOM
        # ne peuvent pas lire leur état réel. L'état est toujours initialisé à False.

    @property
    def is_on(self) -> bool:
        """Retourne l'état de l'interrupteur."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Allume l'interrupteur."""
        _LOGGER.info(
            "🔵 Turn ON: %s (protocol=%s, device_id=%s, house_code=%s, unit_code=%s)",
            self._attr_name,
            self._protocol,
            self._device_id,
            self._house_code,
            self._unit_code,
        )
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
            _LOGGER.info("✅ État mis à jour: ON pour %s", self._attr_name)
        else:
            _LOGGER.error("❌ Échec de l'envoi de la commande ON pour %s", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Éteint l'interrupteur."""
        _LOGGER.info(
            "🔴 Turn OFF: %s (protocol=%s, device_id=%s, house_code=%s, unit_code=%s)",
            self._attr_name,
            self._protocol,
            self._device_id,
            self._house_code,
            self._unit_code,
        )
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
            _LOGGER.info("✅ État mis à jour: OFF pour %s", self._attr_name)
        else:
            _LOGGER.error("❌ Échec de l'envoi de la commande OFF pour %s", self._attr_name)

