"""Intégration RFXCOM pour Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import RFXCOMCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Configure l'intégration RFXCOM au niveau du composant."""
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configure l'intégration RFXCOM."""
    coordinator = RFXCOMCoordinator(hass, entry)
    
    try:
        await coordinator.async_setup()
    except Exception as err:
        _LOGGER.error("Erreur lors de l'initialisation de RFXCOM: %s", err)
        raise ConfigEntryNotReady from err
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge l'intégration RFXCOM."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        coordinator: RFXCOMCoordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Décharger les services si c'est la dernière entrée
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)
    
    return unload_ok

