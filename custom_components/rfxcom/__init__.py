"""Intégration RFXCOM pour Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_DEBUG, DEFAULT_DEBUG
from .coordinator import RFXCOMCoordinator
from .log_handler import setup_log_handler
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

# Handler global pour capturer les logs
_log_handler = None

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Configure l'intégration RFXCOM au niveau du composant."""
    _LOGGER.debug("Configuration de l'intégration RFXCOM au niveau du composant")
    await async_setup_services(hass)
    _LOGGER.debug("Services RFXCOM configurés")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configure l'intégration RFXCOM."""
    global _log_handler
    
    _LOGGER.debug("Configuration de l'entrée RFXCOM: %s", entry.entry_id)
    _LOGGER.debug("Données de configuration: %s", entry.data)
    _LOGGER.debug("Options: %s", entry.options)

    # Configurer le handler de logs si ce n'est pas déjà fait
    if _log_handler is None:
        _log_handler = setup_log_handler()
        # Ajouter le handler à tous les loggers RFXCOM
        for logger_name in [
            "custom_components.rfxcom",
            "custom_components.rfxcom.coordinator",
            "custom_components.rfxcom.switch",
            "custom_components.rfxcom.sensor",
            "custom_components.rfxcom.services",
            "custom_components.rfxcom.config_flow",
        ]:
            logger = logging.getLogger(logger_name)
            logger.addHandler(_log_handler)
            _LOGGER.debug("Handler de logs ajouté à %s", logger_name)

    # Configurer le niveau de log selon l'option debug
    debug_enabled = entry.options.get(CONF_DEBUG, DEFAULT_DEBUG)
    _update_log_level(debug_enabled)

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


def _update_log_level(debug_enabled: bool) -> None:
    """Met à jour le niveau de log selon l'option debug."""
    level = logging.DEBUG if debug_enabled else logging.INFO
    for logger_name in [
        "custom_components.rfxcom",
        "custom_components.rfxcom.coordinator",
        "custom_components.rfxcom.switch",
        "custom_components.rfxcom.sensor",
        "custom_components.rfxcom.services",
        "custom_components.rfxcom.config_flow",
    ]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        _LOGGER.debug("Niveau de log mis à jour pour %s: %s", logger_name, level)


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Met à jour les options de l'intégration."""
    debug_enabled = entry.options.get(CONF_DEBUG, DEFAULT_DEBUG)
    _update_log_level(debug_enabled)

