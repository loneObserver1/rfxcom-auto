"""Services pour l'intégration RFXCOM."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    PROTOCOLS_SWITCH,
    PROTOCOL_TEMP_HUM,
    PROTOCOL_X10,
    PROTOCOL_ARC,
    PROTOCOL_ABICOD,
    PROTOCOL_WAVEMAN,
    PROTOCOL_EMW100,
    PROTOCOL_IMPULS,
    PROTOCOL_RISINGSUN,
    PROTOCOL_PHILIPS,
    PROTOCOL_ENERGENIE,
    PROTOCOL_ENERGENIE_5,
    PROTOCOL_COCOSTICK,
    PROTOCOL_AC,
    PROTOCOL_HOMEEASY_EU,
    PROTOCOL_ANSLUT,
    PROTOCOL_KAMBROOK,
    PROTOCOL_IKEA_KOPPLA,
    PROTOCOL_PT2262,
    PROTOCOL_LIGHTWAVERF,
    PROTOCOL_EMW100_GDO,
    PROTOCOL_BBSB,
    PROTOCOL_RSL,
    PROTOCOL_LIVOLO,
    PROTOCOL_TRC02,
    PROTOCOL_AOKE,
    PROTOCOL_RGB_TRC02,
    PROTOCOL_BLYSS,
    CONF_PROTOCOL,
    CONF_DEVICE_ID,
    CONF_HOUSE_CODE,
    CONF_UNIT_CODE,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_PAIR_DEVICE = "pair_device"

PAIR_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PROTOCOL): vol.In(PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]),
        vol.Required("name"): cv.string,
        vol.Optional(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_HOUSE_CODE): cv.string,
        vol.Optional(CONF_UNIT_CODE): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Configure les services RFXCOM."""

    async def pair_device(call: ServiceCall) -> None:
        """Appaire un nouvel appareil."""
        _LOGGER.debug("Service pair_device appelé: %s", call.data)
        protocol = call.data[CONF_PROTOCOL]
        name = call.data["name"]
        device_id = call.data.get(CONF_DEVICE_ID)
        house_code = call.data.get(CONF_HOUSE_CODE)
        unit_code = call.data.get(CONF_UNIT_CODE)

        _LOGGER.debug(
            "Paramètres: protocol=%s, name=%s, device_id=%s, house_code=%s, unit_code=%s",
            protocol,
            name,
            device_id,
            house_code,
            unit_code,
        )

        # Validation selon le protocole
        lighting1_protocols = [
            PROTOCOL_X10, PROTOCOL_ARC, PROTOCOL_ABICOD, PROTOCOL_WAVEMAN,
            PROTOCOL_EMW100, PROTOCOL_IMPULS, PROTOCOL_RISINGSUN,
            PROTOCOL_PHILIPS, PROTOCOL_ENERGENIE, PROTOCOL_ENERGENIE_5,
            PROTOCOL_COCOSTICK
        ]
        lighting2_protocols = [
            PROTOCOL_AC, PROTOCOL_HOMEEASY_EU, PROTOCOL_ANSLUT, PROTOCOL_KAMBROOK
        ]
        lighting3_protocols = [PROTOCOL_IKEA_KOPPLA]
        lighting4_protocols = [PROTOCOL_PT2262]
        lighting5_protocols = [
            PROTOCOL_LIGHTWAVERF, PROTOCOL_EMW100_GDO, PROTOCOL_BBSB,
            PROTOCOL_RSL, PROTOCOL_LIVOLO, PROTOCOL_TRC02, PROTOCOL_AOKE,
            PROTOCOL_RGB_TRC02
        ]
        lighting6_protocols = [PROTOCOL_BLYSS]

        if protocol in lighting1_protocols:
            if not house_code or not unit_code:
                _LOGGER.error("house_code et unit_code sont requis pour le protocole %s", protocol)
                return
        elif protocol in lighting2_protocols + lighting3_protocols + lighting4_protocols + lighting5_protocols + lighting6_protocols:
            if not device_id:
                _LOGGER.error("device_id est requis pour le protocole %s", protocol)
                return
        elif protocol == PROTOCOL_TEMP_HUM:
            if not device_id:
                _LOGGER.error("device_id est requis pour le protocole TEMP_HUM")
                return

        # Trouver l'entrée de configuration RFXCOM
        entries = hass.config_entries.async_entries(DOMAIN)
        _LOGGER.debug("Intégrations RFXCOM trouvées: %s", len(entries))
        if not entries:
            _LOGGER.error("Aucune intégration RFXCOM configurée")
            return

        entry = entries[0]
        _LOGGER.debug("Utilisation de l'entrée: %s", entry.entry_id)

        # Récupérer la liste actuelle des appareils
        devices = entry.options.get("devices", [])
        _LOGGER.debug("Appareils existants: %s", len(devices))

        # Créer la configuration du nouvel appareil
        device_config = {
            "name": name,
            CONF_PROTOCOL: protocol,
        }

        if protocol in lighting1_protocols:
            device_config[CONF_HOUSE_CODE] = house_code
            device_config[CONF_UNIT_CODE] = unit_code
        elif protocol in lighting2_protocols + lighting3_protocols + lighting4_protocols + lighting5_protocols + lighting6_protocols:
            device_config[CONF_DEVICE_ID] = device_id
            if unit_code:
                device_config[CONF_UNIT_CODE] = unit_code
        elif protocol == PROTOCOL_TEMP_HUM:
            device_config[CONF_DEVICE_ID] = device_id
            # Les données du capteur seront mises à jour automatiquement lors de la réception
            device_config["sensor_data"] = {}

        # Ajouter le nouvel appareil
        devices.append(device_config)
        _LOGGER.debug("Configuration appareil créée: %s", device_config)

        # Mettre à jour les options
        _LOGGER.debug("Mise à jour des options avec %s appareils", len(devices))
        hass.config_entries.async_update_entry(
            entry, options={"devices": devices}
        )

        _LOGGER.info(
            "Appareil appairé: %s (protocole: %s)",
            name,
            protocol,
        )

        # Recharger l'intégration pour créer la nouvelle entité
        _LOGGER.debug("Rechargement de l'intégration pour créer la nouvelle entité")
        await hass.config_entries.async_reload(entry.entry_id)

    hass.services.async_register(
        DOMAIN, SERVICE_PAIR_DEVICE, pair_device, schema=PAIR_DEVICE_SCHEMA
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Décharge les services RFXCOM."""
    hass.services.async_remove(DOMAIN, SERVICE_PAIR_DEVICE)

