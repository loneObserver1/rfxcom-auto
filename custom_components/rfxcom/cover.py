"""Support des volets RFXCOM."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
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
    DEVICE_TYPE_COVER,
)
from .coordinator import RFXCOMCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure les volets RFXCOM."""
    coordinator: RFXCOMCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Charger les appareils configurés
    devices = entry.options.get("devices", [])
    _LOGGER.debug("Configuration de %s volets RFXCOM", len(devices))

    entities = []
    for idx, device_config in enumerate(devices):
        # Ne créer une entité cover que si le type est "cover"
        if device_config.get("device_type") != DEVICE_TYPE_COVER:
            continue
            
        _LOGGER.debug(
            "Création entité cover %s: %s (protocol=%s)",
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
            unique_id = f"{entry.entry_id}_cover_{protocol}_{device_id}_{idx}"
            device_identifier = f"{protocol}_{device_id}"
        elif house_code and unit_code:
            unique_id = f"{entry.entry_id}_cover_{protocol}_{house_code}_{unit_code}_{idx}"
            device_identifier = f"{protocol}_{house_code}_{unit_code}"
        else:
            # Fallback: utiliser le nom et l'index
            name_slug = device_config.get("name", "unknown").lower().replace(" ", "_")
            unique_id = f"{entry.entry_id}_cover_{protocol}_{name_slug}_{idx}"
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
        
        entity = RFXCOMCover(
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

    _LOGGER.info("Création de %s entités cover RFXCOM", len(entities))
    async_add_entities(entities)


class RFXCOMCover(CoordinatorEntity[RFXCOMCoordinator], CoverEntity):
    """Représente un volet RFXCOM."""

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
    )

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
        """Initialise le volet RFXCOM."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_device_info = device_info
        self._protocol = protocol
        self._device_id = device_id
        self._house_code = house_code
        self._unit_code = unit_code
        self._is_closed = None  # État inconnu par défaut

    @property
    def is_closed(self) -> bool | None:
        """Retourne l'état du volet (None = état inconnu)."""
        return self._is_closed

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Ouvre le volet."""
        _LOGGER.info(
            "🔵 Ouvrir volet: %s (protocol=%s, device_id=%s, house_code=%s, unit_code=%s)",
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
            self._is_closed = False
            self.async_write_ha_state()
            _LOGGER.info("✅ État mis à jour: OUVERT pour %s", self._attr_name)
        else:
            _LOGGER.error("❌ Échec de l'envoi de la commande OPEN pour %s", self._attr_name)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Ferme le volet."""
        _LOGGER.info(
            "🔴 Fermer volet: %s (protocol=%s, device_id=%s, house_code=%s, unit_code=%s)",
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
            self._is_closed = True
            self.async_write_ha_state()
            _LOGGER.info("✅ État mis à jour: FERMÉ pour %s", self._attr_name)
        else:
            _LOGGER.error("❌ Échec de l'envoi de la commande CLOSE pour %s", self._attr_name)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Arrête le volet."""
        _LOGGER.info(
            "⏸️  Arrêter volet: %s (protocol=%s, device_id=%s, house_code=%s, unit_code=%s)",
            self._attr_name,
            self._protocol,
            self._device_id,
            self._house_code,
            self._unit_code,
        )
        
        # Pour ARC, on utilise généralement l'unit code 3 pour STOP
        # Si l'unit_code est 1, on envoie ON sur unit 3
        # Sinon, on envoie ON sur le même unit_code (certains volets utilisent cette méthode)
        stop_unit_code = "3" if self._unit_code == "1" else self._unit_code
        
        success = await self.coordinator.send_command(
            protocol=self._protocol,
            device_id=self._device_id or "",
            command=CMD_ON,
            house_code=self._house_code,
            unit_code=stop_unit_code,
        )

        if success:
            _LOGGER.info("✅ Commande STOP envoyée pour %s", self._attr_name)
        else:
            _LOGGER.error("❌ Échec de l'envoi de la commande STOP pour %s", self._attr_name)


