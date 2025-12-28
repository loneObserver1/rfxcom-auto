"""Intégration RFXCOM pour Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry

from .const import (
    DOMAIN,
    CONF_DEBUG,
    DEFAULT_DEBUG,
    CONF_PROTOCOL,
    CONF_DEVICE_ID,
    CONF_HOUSE_CODE,
    CONF_UNIT_CODE,
)
from .coordinator import RFXCOMCoordinator
from .log_handler import setup_log_handler
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

# Handler global pour capturer les logs
_log_handler = None

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR, Platform.COVER]


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
    
    # Vérifier la présence de Node.js si connexion USB (pour toutes les commandes)
    connection_type = entry.data.get("connection_type")
    if connection_type == "usb":
        _LOGGER.info("🔍 Vérification de Node.js pour le bridge RFXCOM (connexion USB)...")
        try:
            import asyncio
            import subprocess
            process = await asyncio.create_subprocess_exec(
                "node",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                version = stdout.decode().strip()
                _LOGGER.info("✅ Node.js détecté: %s - Le bridge Node.js sera utilisé pour toutes les commandes", version)
            else:
                _LOGGER.warning("⚠️ Node.js non disponible - Tentative d'installation automatique...")
        except FileNotFoundError:
            _LOGGER.warning("⚠️ Node.js non installé - Tentative d'installation automatique...")
        except Exception as e:
            _LOGGER.warning("⚠️ Erreur lors de la vérification de Node.js: %s - Tentative d'installation automatique...", e)
    elif connection_type == "network":
        _LOGGER.info("ℹ️ Connexion réseau détectée - Node.js non requis (fonctionne uniquement en USB)")
        _LOGGER.info("💡 Pour utiliser Node.js (recommandé pour meilleure compatibilité), configurez une connexion USB")

    # Configurer le handler de logs si ce n'est pas déjà fait
    if _log_handler is None:
        _log_handler = setup_log_handler()
        # Ajouter le handler à tous les loggers RFXCOM
        for logger_name in [
            "custom_components.rfxcom",
            "custom_components.rfxcom.coordinator",
            "custom_components.rfxcom.switch",
            "custom_components.rfxcom.sensor",
            "custom_components.rfxcom.cover",
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

    # Créer le device hub principal dans le device registry
    device_registry = dr.async_get(hass)
    # Ne pas spécifier de manufacturer pour éviter le 404 sur brands.home-assistant.io
    # Home Assistant cherche l'icône du manufacturer sur brands.home-assistant.io
    # En ne spécifiant pas de manufacturer, on évite cette recherche
    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="RFXCOM",
        # manufacturer="RFXCOM",  # Commenté pour éviter le 404 sur brands.home-assistant.io
        model="RFXtrx",
        sw_version=entry.data.get("version", "1.0.7"),
    )
    # Mettre à jour l'icône du device directement
    try:
        device_registry.async_update_device(
            device_entry.id,
            icon="mdi:radio",
        )
        _LOGGER.info("✅ Icône 'mdi:radio' définie pour le device hub RFXCOM")
    except (AttributeError, TypeError) as e:
        # async_update_device peut ne pas avoir le paramètre icon dans certaines versions
        _LOGGER.debug("async_update_device ne supporte pas le paramètre icon: %s", e)
        _LOGGER.info("💡 Pour définir l'icône, allez dans Paramètres > Appareils > RFXCOM > Icône et sélectionnez 'mdi:radio'")
    except Exception as e:
        _LOGGER.warning("⚠️ Impossible de définir l'icône du device: %s", e)
        _LOGGER.info("💡 Pour définir l'icône manuellement, allez dans Paramètres > Appareils > RFXCOM > Icône et sélectionnez 'mdi:radio'")
    _LOGGER.debug("Device hub RFXCOM créé dans le device registry")

    _LOGGER.debug("Configuration des plateformes: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Écouter les mises à jour du device registry pour synchroniser avec les options
    # Utiliser async_track_device_registry_updated_event pour écouter les changements
    from homeassistant.helpers.event import async_track_device_registry_updated_event
    
    @callback
    def async_device_registry_updated(event: dr.EventDeviceRegistryUpdatedData) -> None:
        """Synchronise les changements du device registry avec les options."""
        if event["action"] != "update":
            return
        
        device_id = event["device_id"]
        if not device_id:
            return
        
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        if not device or entry.entry_id not in device.config_entries:
            return
        
        # Vérifier si c'est un device RFXCOM (pas le hub principal)
        identifiers = device.identifiers
        if not identifiers or (DOMAIN, entry.entry_id) in identifiers:
            # C'est le hub principal, on ne fait rien
            return
        
        # Trouver le device_identifier dans les identifiers
        device_identifier = None
        for domain, identifier in identifiers:
            if domain == DOMAIN:
                device_identifier = identifier
                break
        
        if not device_identifier:
            return
        
        # Trouver l'appareil correspondant dans les options
        devices = list(entry.options.get("devices", []))
        device_idx = None
        
        for idx, dev_config in enumerate(devices):
            protocol = dev_config.get(CONF_PROTOCOL, "")
            device_id_config = dev_config.get(CONF_DEVICE_ID)
            house_code = dev_config.get(CONF_HOUSE_CODE)
            unit_code = dev_config.get(CONF_UNIT_CODE)
            
            # Construire le device_identifier comme dans switch.py
            if device_id_config:
                expected_identifier = f"{protocol}_{device_id_config}_{idx}"
            elif house_code and unit_code:
                expected_identifier = f"{protocol}_{house_code}_{unit_code}_{idx}"
            else:
                name_slug = dev_config.get("name", "unknown").lower().replace(" ", "_")
                expected_identifier = f"{protocol}_{name_slug}_{idx}"
            
            if expected_identifier == device_identifier:
                device_idx = idx
                break
        
        if device_idx is None:
            return
        
        # Mettre à jour le nom dans les options si le nom a changé
        if device.name and device.name != devices[device_idx].get("name"):
            devices[device_idx]["name"] = device.name
            _LOGGER.info("Nom de l'appareil mis à jour depuis le device registry: %s", device.name)
            
            # Mettre à jour les options
            options = dict(entry.options)
            options["devices"] = devices
            hass.config_entries.async_update_entry(entry, options=options)
    
    # Enregistrer le listener
    entry.async_on_unload(
        async_track_device_registry_updated_event(
            hass, [entry.entry_id], async_device_registry_updated
        )
    )
    
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
        "custom_components.rfxcom.cover",
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

