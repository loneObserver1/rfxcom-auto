"""Flux de configuration pour RFXCOM."""
from __future__ import annotations

import logging
from typing import Any

import serial.tools.list_ports
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_BAUDRATE,
    DEFAULT_HOST,
    DEFAULT_NETWORK_PORT,
    CONNECTION_TYPE_USB,
    CONNECTION_TYPE_NETWORK,
    PROTOCOL_AC,
    PROTOCOL_ARC,
    PROTOCOL_TEMP_HUM,
    PROTOCOLS_SWITCH,
    PROTOCOL_X10,
    PROTOCOL_ABICOD,
    PROTOCOL_WAVEMAN,
    PROTOCOL_EMW100,
    PROTOCOL_IMPULS,
    PROTOCOL_RISINGSUN,
    PROTOCOL_PHILIPS,
    PROTOCOL_ENERGENIE,
    PROTOCOL_ENERGENIE_5,
    PROTOCOL_COCOSTICK,
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
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_HOST,
    CONF_NETWORK_PORT,
    CONF_PROTOCOL,
    CONF_UNIT_CODE,
    CONF_HOUSE_CODE,
    CONF_DEVICE_ID,
    CONF_AUTO_REGISTRY,
    CONF_ENABLED_PROTOCOLS,
    CONF_DEBUG,
    PROTOCOL_AUTO,
    DEFAULT_AUTO_REGISTRY,
    DEFAULT_DEBUG,
)

_LOGGER = logging.getLogger(__name__)

STEP_CONNECTION_TYPE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONNECTION_TYPE, default=CONNECTION_TYPE_USB): vol.In(
            [CONNECTION_TYPE_USB, CONNECTION_TYPE_NETWORK]
        ),
    }
)

def _get_available_ports() -> list[str]:
    """Retourne la liste des ports série disponibles."""
    ports = []
    excluded_keywords = ["bluetooth", "debug", "incoming", "jabra", "modem"]

    try:
        available_ports = serial.tools.list_ports.comports()
        for port in available_ports:
            port_str = port.device
            description_lower = (port.description or "").lower()

            # Filtrer les ports qui ne sont probablement pas des ports série RFXCOM
            if any(keyword in description_lower for keyword in excluded_keywords):
                _LOGGER.debug("Port exclu (non RFXCOM): %s (%s)", port_str, port.description)
                continue

            # Filtrer les ports cu.* sur macOS (utiliser tty.*)
            if port_str.startswith("/dev/cu.") and not port_str.startswith("/dev/cu.usbserial"):
                # Sur macOS, préférer tty.* mais garder cu.usbserial
                tty_equivalent = port_str.replace("/dev/cu.", "/dev/tty.")
                if tty_equivalent not in [p.device for p in available_ports]:
                    continue

            ports.append(port_str)
            _LOGGER.debug("Port série détecté: %s (%s)", port_str, port.description or "Sans description")
    except Exception as err:
        _LOGGER.warning("Erreur lors de la détection des ports série: %s", err)

    # Ajouter les ports par défaut s'ils ne sont pas déjà dans la liste
    default_ports = [
        "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2",
        "/dev/ttyACM0", "/dev/ttyACM1",
        "/dev/tty.usbserial", "/dev/tty.usbmodem",
        "COM1", "COM2", "COM3", "COM4",
    ]
    for port in default_ports:
        if port not in ports:
            ports.append(port)

    # Trier les ports (ports USB en premier)
    ports.sort(key=lambda x: (
        0 if "usb" in x.lower() or "usbmodem" in x.lower() or "usbserial" in x.lower() else 1,
        x
    ))

    return ports


def _build_usb_schema() -> vol.Schema:
    """Construit le schéma USB avec les ports disponibles."""
    available_ports = _get_available_ports()

    # Créer les options pour le sélecteur avec descriptions
    port_options = {}
    for port in available_ports:
        try:
            # Essayer d'obtenir plus d'infos sur le port
            port_info = next((p for p in serial.tools.list_ports.comports() if p.device == port), None)
            if port_info:
                label = f"{port} - {port_info.description}" if port_info.description else port
            else:
                label = port
            port_options[port] = label
        except Exception:
            port_options[port] = port

    # Ajouter l'option de saisie manuelle
    port_options["manual"] = "✏️ Saisie manuelle..."

    default_port = DEFAULT_PORT if DEFAULT_PORT in available_ports else (available_ports[0] if available_ports else DEFAULT_PORT)

    schema_dict = {
        vol.Required(CONF_PORT, default=default_port): vol.In(port_options),
        vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.All(
            vol.Coerce(int), vol.In([9600, 19200, 38400, 57600, 115200])
        ),
        vol.Optional(CONF_AUTO_REGISTRY, default=DEFAULT_AUTO_REGISTRY): bool,
        vol.Required(CONF_ENABLED_PROTOCOLS, default=PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]): vol.All(
            cv.multi_select({p: p for p in PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]})
        ),
    }

    return vol.Schema(schema_dict)

def _build_network_schema() -> vol.Schema:
    """Construit le schéma réseau avec sélection de protocoles."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
            vol.Required(CONF_NETWORK_PORT, default=DEFAULT_NETWORK_PORT): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Optional(CONF_AUTO_REGISTRY, default=DEFAULT_AUTO_REGISTRY): bool,
            vol.Required(CONF_ENABLED_PROTOCOLS, default=PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]): vol.All(
                cv.multi_select({p: p for p in PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]})
            ),
        }
    )

def _build_device_schema(enabled_protocols: list[str] | None = None) -> vol.Schema:
    """Construit le schéma pour l'ajout d'appareil avec protocoles activés."""
    if enabled_protocols is None:
        enabled_protocols = PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]
    
    # Ajouter "auto" à la liste des protocoles disponibles
    protocol_options = [PROTOCOL_AUTO] + enabled_protocols
    
    return vol.Schema(
        {
            vol.Required(CONF_PROTOCOL): vol.In(protocol_options),
            vol.Optional(CONF_DEVICE_ID): str,
            vol.Optional(CONF_HOUSE_CODE): str,
            vol.Optional(CONF_UNIT_CODE): str,
            vol.Required("name"): str,
        }
    )


class RFXCOMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère le flux de configuration RFXCOM."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Étape initiale de configuration."""
        # Vérifier qu'il n'existe qu'une seule configuration
        existing_entries = self._async_current_entries()
        if existing_entries:
            return self.async_abort(reason="single_instance_allowed")
        
        if user_input is None:
            # Détecter automatiquement les ports USB disponibles
            try:
                available_ports = await self.hass.async_add_executor_job(
                    serial.tools.list_ports.comports
                )

                # Filtrer pour ne garder que les ports USB réels détectés
                real_usb_ports = []
                excluded_keywords = ["bluetooth", "debug", "incoming", "jabra", "modem"]

                for port in available_ports:
                    port_str = port.device
                    description_lower = (port.description or "").lower()

                    # Exclure les ports non-RFXCOM
                    if any(keyword in description_lower for keyword in excluded_keywords):
                        continue

                    # Vérifier si c'est un port USB réel (pas un port par défaut)
                    is_usb = any(keyword in port_str.lower() for keyword in [
                        "usb", "usbmodem", "usbserial", "ttyusb", "ttyacm"
                    ])

                    # Sur macOS, préférer tty.* mais garder cu.usbserial
                    if port_str.startswith("/dev/cu.") and not port_str.startswith("/dev/cu.usbserial"):
                        tty_equivalent = port_str.replace("/dev/cu.", "/dev/tty.")
                        if tty_equivalent not in [p.device for p in available_ports]:
                            continue

                    if is_usb:
                        real_usb_ports.append(port_str)
                        _LOGGER.debug("Port USB détecté: %s (%s)", port_str, port.description or "Sans description")

                # Si des ports USB sont détectés, afficher directement le formulaire USB
                if real_usb_ports:
                    _LOGGER.info("Ports USB détectés: %s, affichage direct du formulaire USB", real_usb_ports)
                    return await self.async_step_usb()
            except Exception as err:
                _LOGGER.warning("Erreur lors de la détection des ports USB: %s", err)

            # Sinon, afficher le menu de sélection
            return self.async_show_form(
                step_id="user", data_schema=STEP_CONNECTION_TYPE_SCHEMA
            )

        connection_type = user_input.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_USB)

        if connection_type == CONNECTION_TYPE_USB:
            return await self.async_step_usb()
        else:
            return await self.async_step_network()

    async def async_step_usb(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configuration USB."""
        if user_input is None:
            schema = await self.hass.async_add_executor_job(_build_usb_schema)
            return self.async_show_form(
                step_id="usb", data_schema=schema
            )

        errors = {}
        port = user_input.get(CONF_PORT)

        # Si "Saisie manuelle" est sélectionné, demander le port
        if port == "manual":
            return await self.async_step_usb_manual()

        if not port:
            errors["base"] = "port_required"

        if not errors:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_USB
            # Séparer data et options
            data = {k: v for k, v in user_input.items() if k not in [CONF_AUTO_REGISTRY, CONF_ENABLED_PROTOCOLS]}
            options = {
                CONF_AUTO_REGISTRY: user_input.get(CONF_AUTO_REGISTRY, DEFAULT_AUTO_REGISTRY),
                CONF_ENABLED_PROTOCOLS: user_input.get(CONF_ENABLED_PROTOCOLS, PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]),
            }
            return self.async_create_entry(
                title=f"RFXCOM USB ({port})", data=data, options=options
            )

        schema = await self.hass.async_add_executor_job(_build_usb_schema)
        return self.async_show_form(
            step_id="usb", data_schema=schema, errors=errors
        )

    async def async_step_usb_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configuration USB avec saisie manuelle du port."""
        if user_input is None:
            schema = vol.Schema({
                vol.Required(CONF_PORT): str,
                vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.All(
                    vol.Coerce(int), vol.In([9600, 19200, 38400, 57600, 115200])
                ),
                vol.Optional(CONF_AUTO_REGISTRY, default=DEFAULT_AUTO_REGISTRY): bool,
                vol.Required(CONF_ENABLED_PROTOCOLS, default=PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]): vol.All(
                    cv.multi_select({p: p for p in PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]})
                ),
            })
            return self.async_show_form(
                step_id="usb_manual", data_schema=schema
            )

        errors = {}
        if not user_input.get(CONF_PORT):
            errors["base"] = "port_required"

        if not errors:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_USB
            # Séparer data et options
            data = {k: v for k, v in user_input.items() if k not in [CONF_AUTO_REGISTRY, CONF_ENABLED_PROTOCOLS]}
            options = {
                CONF_AUTO_REGISTRY: user_input.get(CONF_AUTO_REGISTRY, DEFAULT_AUTO_REGISTRY),
                CONF_ENABLED_PROTOCOLS: user_input.get(CONF_ENABLED_PROTOCOLS, PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]),
            }
            return self.async_create_entry(
                title=f"RFXCOM USB ({user_input[CONF_PORT]})", data=data, options=options
            )

        schema = vol.Schema({
            vol.Required(CONF_PORT): str,
            vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.All(
                vol.Coerce(int), vol.In([9600, 19200, 38400, 57600, 115200])
            ),
            vol.Optional(CONF_AUTO_REGISTRY, default=DEFAULT_AUTO_REGISTRY): bool,
            vol.Required(CONF_ENABLED_PROTOCOLS, default=PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]): vol.All(
                cv.multi_select({p: p for p in PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]})
            ),
        })
        return self.async_show_form(
            step_id="usb_manual", data_schema=schema, errors=errors
        )

    async def async_step_network(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configuration réseau."""
        if user_input is None:
            schema = _build_network_schema()
            return self.async_show_form(
                step_id="network", data_schema=schema
            )

        errors = {}
        if not user_input.get(CONF_HOST):
            errors["base"] = "host_required"

        if not errors:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_NETWORK
            # Séparer data et options
            data = {k: v for k, v in user_input.items() if k not in [CONF_AUTO_REGISTRY, CONF_ENABLED_PROTOCOLS]}
            options = {
                CONF_AUTO_REGISTRY: user_input.get(CONF_AUTO_REGISTRY, DEFAULT_AUTO_REGISTRY),
                CONF_ENABLED_PROTOCOLS: user_input.get(CONF_ENABLED_PROTOCOLS, PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]),
            }
            return self.async_create_entry(
                title=f"RFXCOM Network ({user_input[CONF_HOST]}:{user_input[CONF_NETWORK_PORT]})",
                data=data,
                options=options,
            )

        schema = _build_network_schema()
        return self.async_show_form(
            step_id="network",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_import(self, import_info: dict[str, Any]) -> FlowResult:
        """Importe une configuration depuis configuration.yaml."""
        return await self.async_step_user(import_info)

    @staticmethod
    async def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Retourne le gestionnaire de flux d'options."""
        return RFXCOMOptionsFlowHandler(config_entry)


class RFXCOMOptionsFlowHandler(config_entries.OptionsFlow):
    """Gère le flux d'options pour RFXCOM."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise le gestionnaire d'options."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Affiche la liste des appareils et les options."""
        devices = self.config_entry.options.get("devices", [])
        auto_registry = self.config_entry.options.get(CONF_AUTO_REGISTRY, DEFAULT_AUTO_REGISTRY)
        debug_enabled = self.config_entry.options.get(CONF_DEBUG, DEFAULT_DEBUG)

        if user_input is None:
            # Créer les options pour le menu
            # Mettre "Ajouter un appareil" en premier pour qu'il soit bien visible
            options = ["add"]
            option_labels = {
                "add": "➕ Ajouter un nouvel appareil",
            }
            
            # Ajouter l'option auto-registry
            options.append("auto_registry")
            option_labels["auto_registry"] = f"🔍 Auto-détection: {'Activée' if auto_registry else 'Désactivée'}"
            
            # Ajouter l'option debug
            options.append("debug")
            option_labels["debug"] = f"🐛 Mode debug: {'Activé' if debug_enabled else 'Désactivé'}"
            
            # Ajouter l'option logs
            options.append("view_logs")
            option_labels["view_logs"] = "📋 Voir les logs"

            # Ajouter les appareils existants
            for idx, device in enumerate(devices):
                device_name = device.get("name", f"Appareil {idx+1}")
                protocol = device.get("protocol", "N/A")
                options.append(f"edit_{idx}")
                options.append(f"delete_{idx}")
                option_labels[f"edit_{idx}"] = f"✏️ Modifier: {device_name} ({protocol})"
                option_labels[f"delete_{idx}"] = f"🗑️ Supprimer: {device_name} ({protocol})"

            schema = vol.Schema({
                vol.Required("action", description={"suggested_value": "add"}): vol.In(options),
            })

            devices_list = "\n".join([
                f"  • {d.get('name', 'Sans nom')} ({d.get('protocol', 'N/A')})"
                for d in devices
            ]) if devices else "  Aucun appareil configuré"

            return self.async_show_form(
                step_id="init",
                data_schema=schema,
                description_placeholders={
                    "devices_count": str(len(devices)),
                    "devices_list": devices_list,
                    "auto_registry_status": "Activée" if auto_registry else "Désactivée",
                    "debug_status": "Activé" if debug_enabled else "Désactivé",
                },
            )

        action = user_input.get("action")
        if action == "add":
            return await self.async_step_add_device()
        elif action == "auto_registry":
            return await self.async_step_auto_registry()
        elif action == "debug":
            return await self.async_step_debug()
        elif action == "view_logs":
            return await self.async_step_view_logs()
        elif action.startswith("edit_"):
            idx = int(action.split("_")[1])
            return await self.async_step_edit_device(idx)
        elif action.startswith("delete_"):
            idx = int(action.split("_")[1])
            return await self.async_step_delete_device(idx)

        return await self.async_step_init()

    async def async_step_auto_registry(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure l'auto-registry."""
        current_value = self.config_entry.options.get(CONF_AUTO_REGISTRY, DEFAULT_AUTO_REGISTRY)

        if user_input is None:
            return self.async_show_form(
                step_id="auto_registry",
                data_schema=vol.Schema({
                    vol.Required(CONF_AUTO_REGISTRY, default=current_value): bool,
                }),
            )

        # Mettre à jour l'option
        options = dict(self.config_entry.options)
        options[CONF_AUTO_REGISTRY] = user_input[CONF_AUTO_REGISTRY]

        return self.async_create_entry(title="", data=options)

    async def async_step_debug(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure le mode debug."""
        current_value = self.config_entry.options.get(CONF_DEBUG, DEFAULT_DEBUG)

        if user_input is None:
            return self.async_show_form(
                step_id="debug",
                data_schema=vol.Schema({
                    vol.Required(CONF_DEBUG, default=current_value): bool,
                }),
            )

        # Mettre à jour l'option
        options = dict(self.config_entry.options)
        options[CONF_DEBUG] = user_input[CONF_DEBUG]
        
        # Mettre à jour le niveau de log immédiatement
        # Import dynamique pour éviter les imports circulaires
        import sys
        import logging
        if "custom_components.rfxcom" in sys.modules:
            rfxcom_module = sys.modules["custom_components.rfxcom"]
            if hasattr(rfxcom_module, "_update_log_level"):
                rfxcom_module._update_log_level(user_input[CONF_DEBUG])
            else:
                # Fallback: mettre à jour directement
                level = logging.DEBUG if user_input[CONF_DEBUG] else logging.INFO
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

        return self.async_create_entry(title="", data=options)

    async def async_step_view_logs(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Affiche les logs RFXCOM."""
        from .log_handler import get_logs, clear_logs
        
        if user_input is None:
            # Récupérer les logs
            logs = get_logs(limit=500)
            
            # Formater les logs pour l'affichage
            if logs:
                logs_text = "\n".join([
                    f"[{log['timestamp']}] [{log['level']}] {log['message']}"
                    for log in logs
                ])
            else:
                logs_text = "Aucun log disponible."
            
            schema = vol.Schema({
                vol.Optional("clear_logs", default=False): bool,
            })
            
            return self.async_show_form(
                step_id="view_logs",
                data_schema=schema,
                description_placeholders={
                    "logs": logs_text,
                    "logs_count": str(len(logs)),
                },
            )
        
        # Si l'utilisateur veut effacer les logs
        if user_input.get("clear_logs"):
            clear_logs()
            return await self.async_step_view_logs()
        
        return await self.async_step_init()

    async def async_step_add_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ajoute un nouvel appareil."""
        # Récupérer les protocoles activés depuis les options
        enabled_protocols = self.config_entry.options.get(
            CONF_ENABLED_PROTOCOLS,
            PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]
        )
        
        if user_input is None:
            schema = _build_device_schema(enabled_protocols)
            return self.async_show_form(
                step_id="add_device", data_schema=schema
            )

        errors = {}

        # Validation selon le protocole
        protocol = user_input[CONF_PROTOCOL]
        
        # Si "auto" est sélectionné, vérifier que l'auto-registry est activée
        if protocol == PROTOCOL_AUTO:
            auto_registry = self.config_entry.options.get(CONF_AUTO_REGISTRY, DEFAULT_AUTO_REGISTRY)
            if not auto_registry:
                errors["base"] = "auto_protocol_requires_auto_registry"
                schema = _build_device_schema(enabled_protocols)
                return self.async_show_form(
                    step_id="add_device", data_schema=schema, errors=errors
                )
            # Pour "auto", on crée un appareil avec protocol="auto"
            # L'appareil sera configuré automatiquement lors de la première détection
            device_config = {
                "name": user_input["name"],
                CONF_PROTOCOL: PROTOCOL_AUTO,
                "auto_detect": True,
            }
            devices = self.config_entry.options.get("devices", [])
            devices.append(device_config)
            return self.async_create_entry(
                title="", data={"devices": devices}
            )

        # Protocoles Lighting1 (house_code + unit_code requis)
        lighting1_protocols = [
            PROTOCOL_X10, PROTOCOL_ARC, PROTOCOL_ABICOD, PROTOCOL_WAVEMAN,
            PROTOCOL_EMW100, PROTOCOL_IMPULS, PROTOCOL_RISINGSUN,
            PROTOCOL_PHILIPS, PROTOCOL_ENERGENIE, PROTOCOL_ENERGENIE_5,
            PROTOCOL_COCOSTICK
        ]

        # Protocoles Lighting2-6 (device_id requis, unit_code optionnel)
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
            if not user_input.get(CONF_HOUSE_CODE) or not user_input.get(CONF_UNIT_CODE):
                errors["base"] = "lighting1_requires_codes"
        elif protocol in lighting2_protocols + lighting3_protocols + lighting4_protocols + lighting5_protocols + lighting6_protocols:
            if not user_input.get(CONF_DEVICE_ID):
                errors[CONF_DEVICE_ID] = "required_for_device_id"
        elif protocol == PROTOCOL_TEMP_HUM:
            if not user_input.get(CONF_DEVICE_ID):
                errors[CONF_DEVICE_ID] = "required_for_temp_hum"

        if not errors:
            # Récupérer les appareils existants
            devices = self.config_entry.options.get("devices", [])

            # Créer la configuration du nouvel appareil
            device_config = {
                "name": user_input["name"],
                CONF_PROTOCOL: protocol,
            }

            # Configurer selon le type de protocole
            if protocol in lighting1_protocols:
                device_config[CONF_HOUSE_CODE] = user_input[CONF_HOUSE_CODE]
                device_config[CONF_UNIT_CODE] = user_input[CONF_UNIT_CODE]
            elif protocol in lighting2_protocols + lighting3_protocols + lighting4_protocols + lighting5_protocols + lighting6_protocols:
                device_config[CONF_DEVICE_ID] = user_input[CONF_DEVICE_ID]
                if user_input.get(CONF_UNIT_CODE):
                    device_config[CONF_UNIT_CODE] = user_input[CONF_UNIT_CODE]
            elif protocol == PROTOCOL_TEMP_HUM:
                device_config[CONF_DEVICE_ID] = user_input[CONF_DEVICE_ID]
                # Les données du capteur seront mises à jour automatiquement lors de la réception
                device_config["sensor_data"] = {}

            # Ajouter le nouvel appareil
            devices.append(device_config)

            # Mettre à jour les options
            return self.async_create_entry(
                title="", data={"devices": devices}
            )

        schema = _build_device_schema(enabled_protocols)
        return self.async_show_form(
            step_id="add_device",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_device(
        self, device_idx: int, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Modifie un appareil existant."""
        devices = self.config_entry.options.get("devices", [])
        if device_idx >= len(devices):
            return await self.async_step_init()

        device = devices[device_idx]

        # Récupérer les protocoles activés depuis les options
        enabled_protocols = self.config_entry.options.get(
            CONF_ENABLED_PROTOCOLS,
            PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]
        )
        
        if user_input is None:
            # Pré-remplir le formulaire avec les valeurs existantes
            protocol_options = [PROTOCOL_AUTO] + enabled_protocols
            schema = vol.Schema({
                vol.Required("name", default=device.get("name")): str,
                vol.Required(CONF_PROTOCOL, default=device.get(CONF_PROTOCOL)): vol.In(protocol_options),
                vol.Optional(CONF_DEVICE_ID, default=device.get(CONF_DEVICE_ID, "")): str,
                vol.Optional(CONF_HOUSE_CODE, default=device.get(CONF_HOUSE_CODE, "")): str,
                vol.Optional(CONF_UNIT_CODE, default=device.get(CONF_UNIT_CODE, "")): str,
            })
            return self.async_show_form(
                step_id="edit_device", data_schema=schema
            )

        # Mettre à jour l'appareil
        protocol = user_input[CONF_PROTOCOL]
        device["name"] = user_input["name"]
        device[CONF_PROTOCOL] = protocol

        # Définir les listes de protocoles (réutiliser celles de add_device)
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
            device[CONF_HOUSE_CODE] = user_input.get(CONF_HOUSE_CODE, "")
            device[CONF_UNIT_CODE] = user_input.get(CONF_UNIT_CODE, "")
            device.pop(CONF_DEVICE_ID, None)
            device.pop("sensor_data", None)
        elif protocol == PROTOCOL_TEMP_HUM:
            device[CONF_DEVICE_ID] = user_input.get(CONF_DEVICE_ID, "")
            device.pop(CONF_HOUSE_CODE, None)
            device.pop(CONF_UNIT_CODE, None)
            # Les données du capteur seront mises à jour automatiquement
            if "sensor_data" not in device:
                device["sensor_data"] = {}

        devices[device_idx] = device

        return self.async_create_entry(
            title="", data={"devices": devices}
        )

    async def async_step_delete_device(
        self, device_idx: int, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Supprime un appareil."""
        devices = self.config_entry.options.get("devices", [])
        if device_idx >= len(devices):
            return await self.async_step_init()

        device_name = devices[device_idx].get("name", f"Appareil {device_idx+1}")

        if user_input is None:
            return self.async_show_form(
                step_id="delete_device",
                data_schema=vol.Schema({
                    vol.Required("confirm", default=False): bool,
                }),
                description_placeholders={"device_name": device_name},
            )

        if user_input.get("confirm"):
            devices.pop(device_idx)
            return self.async_create_entry(
                title="", data={"devices": devices}
            )

        return await self.async_step_init()


async def async_show_pairing_form(
    hass: HomeAssistant,
    protocol: str,
    device_id: str | None = None,
    house_code: str | None = None,
    unit_code: str | None = None,
) -> dict[str, Any]:
    """Affiche le formulaire d'appairage."""
    schema = {
        vol.Required("name"): str,
    }

    if protocol == PROTOCOL_AC:
        schema[vol.Required(CONF_DEVICE_ID, default=device_id or "")] = str
    elif protocol == PROTOCOL_ARC:
        schema[vol.Required(CONF_HOUSE_CODE, default=house_code or "")] = str
        schema[vol.Required(CONF_UNIT_CODE, default=unit_code or "")] = str

    return schema

