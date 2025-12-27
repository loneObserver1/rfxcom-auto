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

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Configure l'intégration RFXCOM au niveau du composant."""
    _LOGGER.debug("Configuration de l'intégration RFXCOM au niveau du composant")
    await async_setup_services(hass)
    _LOGGER.debug("Services RFXCOM configurés")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configure l'intégration RFXCOM."""
    _LOGGER.debug("Configuration de l'entrée RFXCOM: %s", entry.entry_id)
    _LOGGER.debug("Données de configuration: %s", entry.data)
    _LOGGER.debug("Options: %s", entry.options)

    coordinator = RFXCOMCoordinator(hass, entry)

    try:
        _LOGGER.debug("Initialisation du coordinateur...")
        await coordinator.async_setup()
        _LOGGER.debug("Coordinateur initialisé avec succès")
    except Exception as err:
        _LOGGER.error("Erreur lors de l'initialisation de RFXCOM: %s", err)
        raise ConfigEntryNotReady from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    _LOGGER.debug("Coordinateur enregistré dans hass.data")

    _LOGGER.debug("Configuration des plateformes: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("Intégration RFXCOM configurée avec succès")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge l'intégration RFXCOM."""
    _LOGGER.debug("Déchargement de l'entrée RFXCOM: %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    _LOGGER.debug("Plateformes déchargées: %s", unload_ok)

    if unload_ok:
        coordinator: RFXCOMCoordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.debug("Arrêt du coordinateur...")
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("Coordinateur retiré de hass.data")

        # Décharger les services si c'est la dernière entrée
        if not hass.data[DOMAIN]:
            _LOGGER.debug("Dernière entrée, déchargement des services")
            await async_unload_services(hass)
        else:
            _LOGGER.debug("Autres entrées présentes, services conservés")

    _LOGGER.info("Intégration RFXCOM déchargée: %s", unload_ok)
    return unload_ok

