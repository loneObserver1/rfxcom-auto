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
    DEVICE_TYPE_SWITCH,
    DEVICE_TYPE_COVER,
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
    PAIRING_TIMEOUT,
    CMD_ON,
)

_LOGGER = logging.getLogger(__name__)

# STEP_CONNECTION_TYPE_SCHEMA supprimé - plus de choix de type de connexion, USB par défaut

def _get_available_ports() -> tuple[list[str], str | None]:
    """Retourne la liste des ports série disponibles et le port RFXCOM détecté.
    
    Returns:
        Tuple (liste des ports, port RFXCOM par défaut ou None)
    """
    ports = []
    rfxcom_port = None
    excluded_keywords = ["bluetooth", "debug", "incoming", "jabra", "modem"]
    rfxcom_keywords = ["rfxcom", "rfxtrx", "rfx", "433mhz"]

    try:
        available_ports = serial.tools.list_ports.comports()
        for port in available_ports:
            port_str = port.device
            description_lower = (port.description or "").lower()
            manufacturer_lower = (port.manufacturer or "").lower()

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
            
            # Détecter si c'est un port RFXCOM (priorité)
            if rfxcom_port is None:
                if any(keyword in description_lower for keyword in rfxcom_keywords) or \
                   any(keyword in manufacturer_lower for keyword in rfxcom_keywords):
                    rfxcom_port = port_str
                    _LOGGER.info("✅ Port RFXCOM détecté automatiquement: %s (%s)", port_str, port.description or port.manufacturer or "Sans description")
    except Exception as err:
        _LOGGER.warning("Erreur lors de la détection des ports série: %s", err)

    # Ajouter les ports par défaut s'ils ne sont pas déjà dans la liste
    default_ports = [
        "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2",
        "/dev/ttyACM0", "/dev/ttyACM1",
        "/dev/tty.usbserial", "/dev/tty.usbmodem",
        "/dev/cu.usbserial", "/dev/cu.usbmodem",  # macOS call-out ports
        "COM1", "COM2", "COM3", "COM4",
    ]
    for port in default_ports:
        if port not in ports:
            ports.append(port)
    
    # Si aucun port USB réel n'a été détecté, s'assurer que les ports par défaut sont bien présents
    # Cela peut arriver dans Docker où les périphériques USB ne sont pas directement accessibles
    usb_ports_found = any("usb" in p.lower() or "acm" in p.lower() or "serial" in p.lower() for p in ports)
    if not usb_ports_found:
        _LOGGER.debug("Aucun port USB détecté, ajout des ports par défaut pour Docker/macOS")
        # Ajouter des ports génériques qui pourraient être mappés via Docker Desktop USB ou tunnel
        additional_ports = [
            "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2",
            "/dev/ttyACM0", "/dev/ttyACM1",
        ]
        for port in additional_ports:
            if port not in ports:
                ports.insert(0, port)  # Insérer au début pour qu'ils apparaissent en premier

    # Trier les ports (port RFXCOM en premier, puis ports USB)
    ports.sort(key=lambda x: (
        0 if x == rfxcom_port else (1 if "usb" in x.lower() or "usbmodem" in x.lower() or "usbserial" in x.lower() else 2),
        x
    ))

    return ports, rfxcom_port


def _build_usb_schema() -> vol.Schema:
    """Construit le schéma USB avec les ports disponibles."""
    available_ports, rfxcom_port = _get_available_ports()

    # Créer les options pour le sélecteur avec descriptions
    port_options = {}
    for port in available_ports:
        try:
            # Essayer d'obtenir plus d'infos sur le port
            port_info = next((p for p in serial.tools.list_ports.comports() if p.device == port), None)
            if port_info:
                # Marquer le port RFXCOM détecté
                if port == rfxcom_port:
                    label = f"{port} - {port_info.description} (RFXCOM détecté)" if port_info.description else f"{port} (RFXCOM détecté)"
                else:
                    label = f"{port} - {port_info.description}" if port_info.description else port
            else:
                label = f"{port} (RFXCOM détecté)" if port == rfxcom_port else port
            port_options[port] = label
        except Exception:
            port_options[port] = f"{port} (RFXCOM détecté)" if port == rfxcom_port else port

    # Ajouter l'option de saisie manuelle
    port_options["manual"] = "✏️ Saisie manuelle..."

    # Utiliser le port RFXCOM détecté par défaut, sinon le premier port disponible
    default_port = rfxcom_port if rfxcom_port else (DEFAULT_PORT if DEFAULT_PORT in available_ports else (available_ports[0] if available_ports else DEFAULT_PORT))

    schema_dict = {
        vol.Required(CONF_PORT, default=default_port): vol.In(port_options),
        vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.All(
            vol.Coerce(int), vol.In([9600, 19200, 38400, 57600, 115200])
        ),
        vol.Optional(CONF_AUTO_REGISTRY, default=DEFAULT_AUTO_REGISTRY): bool,
        vol.Required(CONF_ENABLED_PROTOCOLS, default=[]): vol.All(
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
            vol.Required(CONF_ENABLED_PROTOCOLS, default=[]): vol.All(
                cv.multi_select({p: p for p in PROTOCOLS_SWITCH + [PROTOCOL_TEMP_HUM]})
            ),
        }
    )

def _build_device_schema(enabled_protocols: list[str] | None = None, protocol: str | None = None) -> vol.Schema:
    """Construit le schéma pour l'ajout d'appareil avec protocoles activés."""
    if enabled_protocols is None:
        enabled_protocols = []
    
    # Ne plus inclure PROTOCOL_AUTO
    protocol_options = enabled_protocols
    
    # Déterminer quels champs afficher selon le protocole
    lighting1_protocols = [
        PROTOCOL_X10, PROTOCOL_ARC, PROTOCOL_ABICOD, PROTOCOL_WAVEMAN,
        PROTOCOL_EMW100, PROTOCOL_IMPULS, PROTOCOL_RISINGSUN,
        PROTOCOL_PHILIPS, PROTOCOL_ENERGENIE, PROTOCOL_ENERGENIE_5,
        PROTOCOL_COCOSTICK
    ]
    
    schema_dict = {
        vol.Required("name"): str,
        vol.Required(CONF_PROTOCOL): vol.In(protocol_options),
    }
    
    # Si un protocole est déjà sélectionné, afficher seulement les champs pertinents
    if protocol:
        if protocol in lighting1_protocols:
            # Lighting1: house_code et unit_code requis, pas device_id
            schema_dict[vol.Required(CONF_HOUSE_CODE)] = str
            schema_dict[vol.Required(CONF_UNIT_CODE)] = str
        elif protocol == PROTOCOL_TEMP_HUM:
            # TEMP_HUM: device_id requis
            schema_dict[vol.Required(CONF_DEVICE_ID)] = str
        else:
            # Lighting2-6: device_id requis, unit_code optionnel
            schema_dict[vol.Required(CONF_DEVICE_ID)] = str
            schema_dict[vol.Optional(CONF_UNIT_CODE)] = str
    else:
        # Pas de protocole sélectionné: afficher tous les champs comme optionnels
        # L'utilisateur sélectionnera d'abord le protocole
        schema_dict[vol.Optional(CONF_DEVICE_ID)] = str
        schema_dict[vol.Optional(CONF_HOUSE_CODE)] = str
        schema_dict[vol.Optional(CONF_UNIT_CODE)] = str
    
    return vol.Schema(schema_dict)


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
            # Si une configuration existe déjà, rediriger vers les options pour ajouter un appareil
            # Cela permet d'ajouter des appareils depuis le menu "Ajouter un appareil"
            existing_entry = existing_entries[0]
            # Rediriger vers le flow d'options via le flow manager
            return self.async_abort(reason="single_instance_allowed")
        
        # Toujours utiliser USB, pas de choix de type de connexion
        return await self.async_step_usb()

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
                CONF_ENABLED_PROTOCOLS: user_input.get(CONF_ENABLED_PROTOCOLS, []),
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
                vol.Required(CONF_ENABLED_PROTOCOLS, default=[]): vol.All(
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
                CONF_ENABLED_PROTOCOLS: user_input.get(CONF_ENABLED_PROTOCOLS, []),
            }
            return self.async_create_entry(
                title=f"RFXCOM ({user_input[CONF_PORT]})", data=data, options=options
            )

        schema = vol.Schema({
            vol.Required(CONF_PORT): str,
            vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.All(
                vol.Coerce(int), vol.In([9600, 19200, 38400, 57600, 115200])
            ),
            vol.Optional(CONF_AUTO_REGISTRY, default=DEFAULT_AUTO_REGISTRY): bool,
            vol.Required(CONF_ENABLED_PROTOCOLS, default=[]): vol.All(
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
                CONF_ENABLED_PROTOCOLS: user_input.get(CONF_ENABLED_PROTOCOLS, []),
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
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Retourne le gestionnaire de flux d'options."""
        return RFXCOMOptionsFlowHandler()


class RFXCOMOptionsFlowHandler(config_entries.OptionsFlow):
    """Gère le flux d'options pour RFXCOM."""
    
    def __getattr__(self, name: str):
        """Intercepte les appels dynamiques à async_step_edit_device_* et async_step_delete_device_*."""
        if name.startswith("async_step_edit_device_"):
            # Extraire l'index depuis le nom de la méthode
            # Format: async_step_edit_device_0, async_step_edit_device_1, etc.
            try:
                idx_str = name.replace("async_step_edit_device_", "")
                device_idx = int(idx_str)
                # Retourner une méthode qui appelle async_step_edit_device
                async def edit_wrapper(user_input=None):
                    return await self.async_step_edit_device(device_idx, user_input)
                return edit_wrapper
            except (ValueError, AttributeError):
                raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        elif name.startswith("async_step_delete_device_"):
            # Extraire l'index depuis le nom de la méthode
            # Format: async_step_delete_device_0, async_step_delete_device_1, etc.
            try:
                idx_str = name.replace("async_step_delete_device_", "")
                device_idx = int(idx_str)
                # Retourner une méthode qui appelle async_step_delete_device
                # Home Assistant appelle la méthode avec user_input comme premier argument
                async def delete_wrapper(user_input=None):
                    # Vérifier que user_input n'est pas l'index (au cas où)
                    if isinstance(user_input, int):
                        # Si c'est un int, c'est probablement device_idx qui a été passé par erreur
                        return await self.async_step_delete_device(user_input, None)
                    return await self.async_step_delete_device(device_idx, user_input)
                return delete_wrapper
            except (ValueError, AttributeError):
                raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Menu principal des options."""
        devices = self.config_entry.options.get("devices", [])
        
        # Construire la liste des options
        menu_options = {
            "add": "➕ Ajouter un appareil",
        }
        
        # Ajouter les options pour chaque appareil
        for idx, device in enumerate(devices):
            device_name = device.get("name", f"Appareil {idx+1}")
            menu_options[f"edit_device_{idx}"] = f"✏️ Modifier: {device_name}"
            menu_options[f"delete_device_{idx}"] = f"🗑️ Supprimer: {device_name}"
        
        # Ajouter les autres options
        menu_options["auto_registry"] = "🔍 Auto-registry"
        
        # async_show_menu() appelle directement async_step_{next_step_id}
        # Les clés du dictionnaire menu_options deviennent les next_step_id
        return self.async_show_menu(
            step_id="init",
            menu_options=menu_options,
        )
    

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
            
            # Limiter la taille pour l'affichage (Home Assistant a des limites)
            # Afficher les 200 derniers logs maximum
            if logs and len(logs) > 200:
                logs_display = logs[-200:]
                logs_text = f"... ({len(logs) - 200} logs plus anciens) ...\n\n" + "\n".join([
                    f"[{log['timestamp']}] [{log['level']}] {log['message']}"
                    for log in logs_display
                ])
            elif logs:
                logs_text = "\n".join([
                    f"[{log['timestamp']}] [{log['level']}] {log['message']}"
                    for log in logs
                ])
            
            # Créer un schéma avec les actions
            schema = vol.Schema({
                vol.Required("action", default="back"): vol.In({
                    "back": "← Retour",
                    "clear": "🗑️ Effacer les logs",
                    "refresh": "🔄 Rafraîchir",
                }),
            })
            
            return self.async_show_form(
                step_id="view_logs",
                data_schema=schema,
                description_placeholders={
                    "logs": logs_text[:50000] if logs_text else "Aucun log disponible.",  # Limite de 50KB
                    "logs_count": str(len(logs)),
                },
            )
        
        # Gérer les actions
        action = user_input.get("action")
        if action == "clear":
            clear_logs()
            return await self.async_step_view_logs()
        elif action == "refresh":
            return await self.async_step_view_logs()
        elif action == "back" or not action:
            return await self.async_step_init()
        
        return await self.async_step_init()

    async def async_step_add(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ajoute un nouvel appareil - Choix du mode."""
        if user_input is None:
            # Demander le mode d'ajout
            schema = vol.Schema({
                vol.Required("pairing_mode", default="auto"): vol.In({
                    "auto": "🔍 Appairage automatique (recommandé)",
                    "manual": "✏️ Saisie manuelle",
                }),
            })
            return self.async_show_form(
                step_id="add",
                data_schema=schema,
                description_placeholders={
                    "instructions": (
                        "**Appairage automatique** : Mettez l'appareil en mode appairage, "
                        "puis le système enverra une commande et détectera automatiquement l'appareil.\n\n"
                        "**Saisie manuelle** : Entrez manuellement les informations de l'appareil."
                    ),
                },
            )
        
        pairing_mode = user_input.get("pairing_mode", "manual")
        
        if pairing_mode == "auto":
            # Rediriger vers le mode automatique
            return await self.async_step_pair_device()
        else:
            # Rediriger vers le mode manuel
            return await self.async_step_add_device_manual()
    
    async def async_step_add_device_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ajoute un appareil en mode manuel."""
        # Récupérer les protocoles activés depuis les options
        enabled_protocols = self.config_entry.options.get(
            CONF_ENABLED_PROTOCOLS,
            []
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
        
        if user_input is None:
            # Étape 1: Sélectionner le protocole, le nom et le type d'appareil
            protocol_options = enabled_protocols
            # Pour TEMP_HUM, le device_type est automatiquement "sensor", donc on ne le demande pas
            schema_dict = {
                vol.Required("name"): str,
                vol.Required(CONF_PROTOCOL): vol.In(protocol_options),
            }
            # Ne proposer device_type que si le protocole n'est pas TEMP_HUM
            # (on ne sait pas encore le protocole à ce stade, donc on le propose toujours)
            schema_dict[vol.Optional("device_type", default="switch")] = vol.In(["switch", "cover"])
            schema = vol.Schema(schema_dict)
            return self.async_show_form(
                step_id="add_device_manual", data_schema=schema
            )

        errors = {}

        # Validation selon le protocole
        protocol = user_input[CONF_PROTOCOL]
        
        # Pour TEMP_HUM, le device_type est automatiquement "sensor" (pas besoin d'appairage)
        if protocol == PROTOCOL_TEMP_HUM:
            user_input["device_type"] = DEVICE_TYPE_SENSOR
        
        # Si le protocole est sélectionné mais pas les champs spécifiques, passer à l'étape 2
        if protocol:
            if protocol in lighting1_protocols:
                # Lighting1: besoin de house_code et unit_code
                if not user_input.get(CONF_HOUSE_CODE) or not user_input.get(CONF_UNIT_CODE):
                    # Étape 2: Demander house_code et unit_code
                    schema = vol.Schema({
                        vol.Required("name", default=user_input.get("name", "")): str,
                        vol.Required(CONF_PROTOCOL, default=protocol): vol.In([protocol]),
                        vol.Required(CONF_HOUSE_CODE): str,
                        vol.Required(CONF_UNIT_CODE): str,
                    })
                    return self.async_show_form(
                        step_id="add_device_manual", data_schema=schema
                    )
            elif protocol == PROTOCOL_TEMP_HUM:
                # TEMP_HUM: besoin de device_id
                if not user_input.get(CONF_DEVICE_ID):
                    schema = vol.Schema({
                        vol.Required("name", default=user_input.get("name", "")): str,
                        vol.Required(CONF_PROTOCOL, default=protocol): vol.In([protocol]),
                        vol.Required(CONF_DEVICE_ID): str,
                    })
                    return self.async_show_form(
                        step_id="add_device_manual", data_schema=schema
                    )
            else:
                # Lighting2-6: besoin de device_id, unit_code optionnel (1 par défaut pour AC)
                if not user_input.get(CONF_DEVICE_ID):
                    schema = vol.Schema({
                        vol.Required("name", default=user_input.get("name", "")): str,
                        vol.Required(CONF_PROTOCOL, default=protocol): vol.In([protocol]),
                        vol.Required(CONF_DEVICE_ID): str,
                        vol.Optional(CONF_UNIT_CODE, default="1"): str,  # Par défaut 1 pour AC
                    })
                    return self.async_show_form(
                        step_id="add_device_manual", data_schema=schema
                    )
        

        # Validation supplémentaire (déjà fait plus haut pour Lighting1)
        if protocol in lighting2_protocols + lighting3_protocols + lighting4_protocols + lighting5_protocols + lighting6_protocols:
            if not user_input.get(CONF_DEVICE_ID):
                schema = _build_device_schema(enabled_protocols, protocol=protocol)
                errors[CONF_DEVICE_ID] = "required_for_device_id"
                return self.async_show_form(
                    step_id="add_device_manual", data_schema=schema, errors=errors
                )
        elif protocol == PROTOCOL_TEMP_HUM:
            if not user_input.get(CONF_DEVICE_ID):
                schema = _build_device_schema(enabled_protocols, protocol=protocol)
                errors[CONF_DEVICE_ID] = "required_for_temp_hum"
                return self.async_show_form(
                    step_id="add_device_manual", data_schema=schema, errors=errors
                )

        if not errors:
            # Récupérer les appareils existants
            devices = self.config_entry.options.get("devices", [])

            # Créer la configuration du nouvel appareil
            device_config = {
                "name": user_input["name"],
                CONF_PROTOCOL: protocol,
            }
            
            # Sauvegarder le device_type (switch par défaut, sauf pour TEMP_HUM)
            if protocol == PROTOCOL_TEMP_HUM:
                device_config["device_type"] = DEVICE_TYPE_SENSOR
            else:
                device_config["device_type"] = user_input.get("device_type", DEVICE_TYPE_SWITCH)

            # Configurer selon le type de protocole
            if protocol in lighting1_protocols:
                device_config[CONF_HOUSE_CODE] = user_input[CONF_HOUSE_CODE]
                device_config[CONF_UNIT_CODE] = user_input[CONF_UNIT_CODE]
            elif protocol in lighting2_protocols + lighting3_protocols + lighting4_protocols + lighting5_protocols + lighting6_protocols:
                device_config[CONF_DEVICE_ID] = user_input[CONF_DEVICE_ID]
                # Pour AC, unit_code est généralement 1 (par défaut si non fourni)
                unit_code = user_input.get(CONF_UNIT_CODE, "1")
                if unit_code:
                    device_config[CONF_UNIT_CODE] = unit_code
            elif protocol == PROTOCOL_TEMP_HUM:
                device_config[CONF_DEVICE_ID] = user_input[CONF_DEVICE_ID]
                # Les données du capteur seront mises à jour automatiquement lors de la réception
                device_config["sensor_data"] = {}

            # Ajouter le nouvel appareil
            _LOGGER.info(
                "Ajout d'un nouvel appareil: name=%s, protocol=%s, device_type=%s, device_id=%s, house_code=%s, unit_code=%s",
                device_config.get("name"),
                device_config.get(CONF_PROTOCOL),
                device_config.get("device_type"),
                device_config.get(CONF_DEVICE_ID),
                device_config.get(CONF_HOUSE_CODE),
                device_config.get(CONF_UNIT_CODE),
            )
            devices.append(device_config)
            _LOGGER.info("Liste des appareils après ajout (%d appareils):", len(devices))
            for idx, dev in enumerate(devices):
                _LOGGER.info("  [%d] %s (protocol=%s, device_type=%s)", idx, dev.get("name"), dev.get(CONF_PROTOCOL), dev.get("device_type"))

            # Mettre à jour les options (fusionner avec les options existantes)
            options = dict(self.config_entry.options)
            options["devices"] = devices
            
            # Mettre à jour l'entrée et recharger
            self.hass.config_entries.async_update_entry(
                self.config_entry, options=options
            )
            
            # Recharger l'intégration pour créer la nouvelle entité
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            
            return self.async_create_entry(title="", data=options)

        schema = _build_device_schema(enabled_protocols)
        return self.async_show_form(
            step_id="add_device_manual",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_pair_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Appairage automatique - Étape 1: Protocole et nom."""
        # Récupérer les protocoles activés depuis les options
        enabled_protocols = self.config_entry.options.get(
            CONF_ENABLED_PROTOCOLS,
            []
        )
        
        if user_input is None:
            # Exclure TEMP_HUM de l'appairage automatique car les sondes envoient déjà leurs données
            protocol_options = [p for p in enabled_protocols if p != PROTOCOL_AUTO and p != PROTOCOL_TEMP_HUM]
            schema = vol.Schema({
                vol.Required("name"): str,
                vol.Required(CONF_PROTOCOL): vol.In(protocol_options),
                vol.Optional("device_type", default="switch"): vol.In(["switch", "cover"]),
            })
            return self.async_show_form(
                step_id="pair_device",
                data_schema=schema,
                description_placeholders={
                    "instructions": (
                        "Sélectionnez le protocole de votre appareil et donnez-lui un nom.\n\n"
                        "**Important** : Ne mettez pas encore l'appareil en mode appairage !"
                    ),
                },
            )
        
        # Stocker les données pour l'étape suivante
        device_type = user_input.get("device_type", DEVICE_TYPE_SWITCH)
        self._pairing_data = {
            "name": user_input["name"],
            "protocol": user_input[CONF_PROTOCOL],
            "device_type": device_type,
        }
        
        # Rediriger vers l'étape suivante selon le protocole
        protocol = self._pairing_data["protocol"]
        lighting1_protocols = [
            PROTOCOL_X10, PROTOCOL_ARC, PROTOCOL_ABICOD, PROTOCOL_WAVEMAN,
            PROTOCOL_EMW100, PROTOCOL_IMPULS, PROTOCOL_RISINGSUN,
            PROTOCOL_PHILIPS, PROTOCOL_ENERGENIE, PROTOCOL_ENERGENIE_5,
            PROTOCOL_COCOSTICK
        ]
        
        if protocol in lighting1_protocols:
            return await self.async_step_pair_device_codes()
        elif protocol == PROTOCOL_AC:
            # Pour AC, utiliser le nouveau processus d'appairage amélioré
            return await self.async_step_pair_device_ac_listen()
        else:
            return await self.async_step_pair_device_id()
    
    async def async_step_pair_device_codes(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Appairage automatique - Étape 2: Génération automatique des codes pour Lighting1."""
        if not hasattr(self, '_pairing_data'):
            return await self.async_step_pair_device()
        
        protocol = self._pairing_data["protocol"]
        name = self._pairing_data["name"]
        
        # Récupérer les appareils existants pour éviter les collisions
        devices = self.config_entry.options.get("devices", [])
        
        # Créer un set des combinaisons déjà utilisées
        used_combinations = set()
        for device in devices:
            if device.get(CONF_PROTOCOL) in [
                PROTOCOL_X10, PROTOCOL_ARC, PROTOCOL_ABICOD, PROTOCOL_WAVEMAN,
                PROTOCOL_EMW100, PROTOCOL_IMPULS, PROTOCOL_RISINGSUN,
                PROTOCOL_PHILIPS, PROTOCOL_ENERGENIE, PROTOCOL_ENERGENIE_5,
                PROTOCOL_COCOSTICK
            ]:
                house_code = device.get(CONF_HOUSE_CODE)
                unit_code = device.get(CONF_UNIT_CODE)
                if house_code and unit_code:
                    used_combinations.add((house_code.upper(), str(unit_code)))
        
        # Générer automatiquement les codes (éviter les collisions)
        house_codes = [chr(ord('A') + i) for i in range(16)]  # A-P
        unit_codes = [str(i) for i in range(1, 17)]  # 1-16
        
        selected_house_code = None
        selected_unit_code = None
        
        # Trouver la première combinaison disponible
        for house_code in house_codes:
            for unit_code in unit_codes:
                if (house_code, unit_code) not in used_combinations:
                    selected_house_code = house_code
                    selected_unit_code = unit_code
                    break
            if selected_house_code:
                break
        
        if not selected_house_code or not selected_unit_code:
            # Toutes les combinaisons sont utilisées (peu probable mais possible)
            _LOGGER.error("Toutes les combinaisons de codes sont déjà utilisées")
            return self.async_show_form(
                step_id="pair_device",
                data_schema=vol.Schema({
                    vol.Required("name"): str,
                    vol.Required(CONF_PROTOCOL): vol.In([protocol]),
                }),
                errors={"base": "all_codes_used"},
                description_placeholders={
                    "instructions": (
                        "Toutes les combinaisons de codes sont déjà utilisées. "
                        "Veuillez supprimer un appareil existant ou utiliser le mode manuel."
                    ),
                },
            )
        
        # Stocker les codes générés automatiquement
        self._pairing_data["house_code"] = selected_house_code
        self._pairing_data["unit_code"] = selected_unit_code
        
        _LOGGER.info(
            "✅ Codes générés automatiquement pour %s : House=%s, Unit=%s",
            name,
            selected_house_code,
            selected_unit_code,
        )
        
        # Passer directement à l'étape suivante (pas besoin de formulaire)
        return await self.async_step_pair_device_ready()
    
    async def async_step_pair_device_ac_listen(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Appairage AC - Étape 1: Écouter une action pour récupérer l'ID."""
        from .coordinator import RFXCOMCoordinator
        from . import DOMAIN as RFXCOM_DOMAIN
        import asyncio
        
        if not hasattr(self, '_pairing_data'):
            return await self.async_step_pair_device()
        
        protocol = self._pairing_data["protocol"]
        name = self._pairing_data["name"]
        
        if user_input is None:
            # Activer temporairement l'auto-registry pour écouter
            coordinator: RFXCOMCoordinator = self.hass.data[RFXCOM_DOMAIN][self.config_entry.entry_id]
            original_auto_registry = coordinator.auto_registry
            coordinator.auto_registry = True  # Activer pour écouter
            
            schema = vol.Schema({
                vol.Required("ready_to_listen", default=False): bool,
            })
            return self.async_show_form(
                step_id="pair_device_ac_listen",
                data_schema=schema,
                description_placeholders={
                    "instructions": (
                        f"**Protocole** : {protocol}\n"
                        f"**Nom** : {name}\n\n"
                        "**Étape 1 - Détection de l'appareil** :\n"
                        "1. Utilisez votre télécommande ou appuyez sur le bouton de la prise DIO\n"
                        "2. Envoyez une commande ON ou OFF\n"
                        "3. Le système va écouter et détecter automatiquement l'ID de l'appareil\n"
                        "4. Cochez la case ci-dessous quand vous êtes prêt à envoyer la commande\n\n"
                        "⏱️ Vous avez 30 secondes après avoir coché la case pour envoyer la commande."
                    ),
                },
            )
        
        if not user_input.get("ready_to_listen"):
            schema = vol.Schema({
                vol.Required("ready_to_listen", default=False): bool,
            })
            return self.async_show_form(
                step_id="pair_device_ac_listen",
                data_schema=schema,
                errors={"base": "not_ready"},
                description_placeholders={
                    "instructions": "Veuillez cocher la case pour commencer l'écoute.",
                },
            )
        
        # Écouter les paquets AC pendant 30 secondes
        coordinator: RFXCOMCoordinator = self.hass.data[RFXCOM_DOMAIN][self.config_entry.entry_id]
        original_auto_registry = coordinator.auto_registry
        coordinator.auto_registry = True  # Activer pour écouter
        
        _LOGGER.info("🔍 Écoute des paquets AC pendant 30 secondes...")
        _LOGGER.info("💡 Envoyez une commande ON ou OFF depuis votre télécommande ou appuyez sur le bouton de la prise")
        
        detected_device = None
        start_time = asyncio.get_event_loop().time()
        listen_timeout = 30.0  # 30 secondes
        
        while (asyncio.get_event_loop().time() - start_time) < listen_timeout:
            await asyncio.sleep(0.5)  # Vérifier toutes les 0.5 secondes
            
            # Vérifier si un paquet AC a été reçu
            for unique_id, device_info in coordinator._discovered_devices.items():
                if device_info.get(CONF_PROTOCOL) == PROTOCOL_AC:
                    detected_device = device_info
                    _LOGGER.info("✅ Appareil AC détecté : device_id=%s, unit_code=%s", 
                                device_info.get(CONF_DEVICE_ID), 
                                device_info.get(CONF_UNIT_CODE))
                    break
            
            if detected_device:
                break
        
        # Restaurer l'auto-registry
        coordinator.auto_registry = original_auto_registry
        
        if not detected_device:
            schema = vol.Schema({
                vol.Required("ready_to_listen", default=False): bool,
            })
            return self.async_show_form(
                step_id="pair_device_ac_listen",
                data_schema=schema,
                errors={"base": "no_device_detected"},
                description_placeholders={
                    "instructions": (
                        "❌ Aucun appareil AC détecté.\n\n"
                        "Vérifiez que :\n"
                        "- Vous avez bien envoyé une commande ON ou OFF\n"
                        "- La prise est bien branchée et fonctionne\n"
                        "- Le RFXCOM reçoit bien les signaux\n\n"
                        "Réessayez en cochant la case ci-dessous."
                    ),
                },
            )
        
        # Stocker les informations détectées
        self._pairing_data["device_id"] = detected_device.get(CONF_DEVICE_ID)
        self._pairing_data["unit_code"] = detected_device.get(CONF_UNIT_CODE, "1")
        
        _LOGGER.info("✅ ID détecté : device_id=%s, unit_code=%s", 
                    self._pairing_data["device_id"], 
                    self._pairing_data["unit_code"])
        
        # Passer à l'étape d'appairage
        return await self.async_step_pair_device_ac_pairing()
    
    async def async_step_pair_device_ac_pairing(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Appairage AC - Étape 2: Mise en mode appairage et envoi des commandes."""
        from .coordinator import RFXCOMCoordinator
        from . import DOMAIN as RFXCOM_DOMAIN
        import asyncio
        
        if not hasattr(self, '_pairing_data'):
            return await self.async_step_pair_device()
        
        protocol = self._pairing_data["protocol"]
        name = self._pairing_data["name"]
        device_id = self._pairing_data.get("device_id")
        unit_code = self._pairing_data.get("unit_code", "1")
        
        if user_input is None:
            schema = vol.Schema({
                vol.Required("ready_to_pair", default=False): bool,
            })
            return self.async_show_form(
                step_id="pair_device_ac_pairing",
                data_schema=schema,
                description_placeholders={
                    "instructions": (
                        f"**Protocole** : {protocol}\n"
                        f"**Nom** : {name}\n"
                        f"**Device ID détecté** : {device_id}\n"
                        f"**Unit Code détecté** : {unit_code}\n\n"
                        "**Étape 2 - Appairage** :\n"
                        "1. Mettez la prise DIO en mode appairage (suivez les instructions du fabricant)\n"
                        "   - Généralement : maintenez le bouton appuyé pendant 3-5 secondes\n"
                        "   - La LED doit clignoter pour indiquer le mode appairage\n"
                        "2. Cochez la case ci-dessous quand la prise est en mode appairage\n"
                        "3. Le système va envoyer des commandes d'appairage pendant 4 secondes\n\n"
                        "⏱️ Vous avez 4 secondes de fenêtre d'appairage !"
                    ),
                },
            )
        
        if not user_input.get("ready_to_pair"):
            schema = vol.Schema({
                vol.Required("ready_to_pair", default=False): bool,
            })
            return self.async_show_form(
                step_id="pair_device_ac_pairing",
                data_schema=schema,
                errors={"base": "not_ready"},
                description_placeholders={
                    "instructions": "Veuillez mettre la prise en mode appairage et cocher la case.",
                },
            )
        
        # Récupérer le coordinateur
        coordinator: RFXCOMCoordinator = self.hass.data[RFXCOM_DOMAIN][self.config_entry.entry_id]
        
        # Envoyer des commandes d'appairage (ON répétées) pendant 4 secondes
        _LOGGER.info("📤 Envoi des commandes d'appairage pour device_id=%s, unit_code=%s...", device_id, unit_code)
        
        pair_start_time = asyncio.get_event_loop().time()
        pair_duration = 4.0  # 4 secondes
        send_count = 0
        
        while (asyncio.get_event_loop().time() - pair_start_time) < pair_duration:
            success = await coordinator.send_command(
                protocol=PROTOCOL_AC,
                device_id=device_id,
                command=CMD_ON,
                unit_code=unit_code,
            )
            if success:
                send_count += 1
            await asyncio.sleep(0.05)  # ~20 envois par seconde
        
        _LOGGER.info("✅ %d commandes d'appairage envoyées", send_count)
        
        # Attendre un peu pour que l'appairage se stabilise
        await asyncio.sleep(1)
        
        # Passer à l'étape de test
        return await self.async_step_pair_device_ac_test()
    
    async def async_step_pair_device_ac_test(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Appairage AC - Étape 3: Test ON/OFF pour vérifier l'appairage."""
        from .coordinator import RFXCOMCoordinator
        from . import DOMAIN as RFXCOM_DOMAIN
        import asyncio
        
        if not hasattr(self, '_pairing_data'):
            return await self.async_step_pair_device()
        
        protocol = self._pairing_data["protocol"]
        name = self._pairing_data["name"]
        device_id = self._pairing_data.get("device_id")
        unit_code = self._pairing_data.get("unit_code", "1")
        
        if user_input is None:
            schema = vol.Schema({
                vol.Required("test_result"): vol.In(["success", "failed", "skip"]),
            })
            return self.async_show_form(
                step_id="pair_device_ac_test",
                data_schema=schema,
                description_placeholders={
                    "instructions": (
                        f"**Protocole** : {protocol}\n"
                        f"**Nom** : {name}\n"
                        f"**Device ID** : {device_id}\n"
                        f"**Unit Code** : {unit_code}\n\n"
                        "**Étape 3 - Test de l'appairage** :\n"
                        "Le système va envoyer une séquence de tests :\n"
                        "1. Commande OFF (la prise doit s'éteindre)\n"
                        "2. Attente 2 secondes\n"
                        "3. Commande ON (la prise doit s'allumer)\n"
                        "4. Attente 2 secondes\n"
                        "5. Commande OFF (la prise doit s'éteindre)\n\n"
                        "Observez la prise et indiquez le résultat :"
                    ),
                },
            )
        
        # Récupérer le coordinateur
        coordinator: RFXCOMCoordinator = self.hass.data[RFXCOM_DOMAIN][self.config_entry.entry_id]
        
        if user_input.get("test_result") == "skip":
            _LOGGER.info("⏭️ Test ignoré par l'utilisateur")
        else:
            # Envoyer la séquence de test
            _LOGGER.info("🧪 Démarrage du test ON/OFF...")
            
            # OFF
            _LOGGER.info("📤 Test 1/3 : Envoi OFF...")
            await coordinator.send_command(
                protocol=PROTOCOL_AC,
                device_id=device_id,
                command=CMD_OFF,
                unit_code=unit_code,
            )
            await asyncio.sleep(2)
            
            # ON
            _LOGGER.info("📤 Test 2/3 : Envoi ON...")
            await coordinator.send_command(
                protocol=PROTOCOL_AC,
                device_id=device_id,
                command=CMD_ON,
                unit_code=unit_code,
            )
            await asyncio.sleep(2)
            
            # OFF
            _LOGGER.info("📤 Test 3/3 : Envoi OFF...")
            await coordinator.send_command(
                protocol=PROTOCOL_AC,
                device_id=device_id,
                command=CMD_OFF,
                unit_code=unit_code,
            )
            
            _LOGGER.info("✅ Séquence de test terminée")
        
        if user_input.get("test_result") == "failed":
            # L'appairage a échoué, proposer de réessayer
            schema = vol.Schema({
                vol.Required("retry", default=False): bool,
            })
            return self.async_show_form(
                step_id="pair_device_ac_test",
                data_schema=schema,
                errors={"base": "test_failed"},
                description_placeholders={
                    "instructions": (
                        "❌ Le test a échoué. La prise ne répond pas aux commandes.\n\n"
                        "Vérifiez que :\n"
                        "- La prise est bien en mode appairage\n"
                        "- Le Device ID et Unit Code sont corrects\n"
                        "- La prise est bien branchée et fonctionne\n\n"
                        "Souhaitez-vous réessayer l'appairage ?"
                    ),
                },
            )
        
        # Appairage réussi, créer la configuration
        devices = self.config_entry.options.get("devices", [])
        device_type = self._pairing_data.get("device_type", DEVICE_TYPE_SWITCH)
        device_config = {
            "name": name,
            CONF_PROTOCOL: protocol,
            "device_type": device_type,
            CONF_DEVICE_ID: device_id,
            CONF_UNIT_CODE: unit_code,
        }
        
        devices.append(device_config)
        
        # Mettre à jour les options
        options = dict(self.config_entry.options)
        options["devices"] = devices
        
        # Mettre à jour l'entrée et recharger
        self.hass.config_entries.async_update_entry(
            self.config_entry, options=options
        )
        
        # Recharger l'intégration pour créer la nouvelle entité
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        
        _LOGGER.info(
            "✅ Appareil AC appairé avec succès : %s (device_id=%s, unit_code=%s)",
            name, device_id, unit_code
        )
        
        return self.async_create_entry(title="", data=options)
    
    async def async_step_pair_device_id(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Appairage automatique - Étape 2: ID pour Lighting2-6 (sauf AC)."""
        if not hasattr(self, '_pairing_data'):
            return await self.async_step_pair_device()
        
        protocol = self._pairing_data["protocol"]
        name = self._pairing_data["name"]
        
        if user_input is None:
            schema = vol.Schema({
                vol.Required(CONF_DEVICE_ID): str,
            })
            return self.async_show_form(
                step_id="pair_device_id",
                data_schema=schema,
                description_placeholders={
                    "instructions": (
                        f"**Protocole** : {protocol}\n"
                        f"**Nom** : {name}\n\n"
                        "Entrez l'ID de l'appareil (format hexadécimal) "
                        "que vous souhaitez utiliser pour cet appareil."
                    ),
                },
            )
        
        # Stocker l'ID
        self._pairing_data["device_id"] = user_input[CONF_DEVICE_ID]
        
        # Passer à l'étape suivante
        return await self.async_step_pair_device_ready()
    
    async def async_step_pair_device_ready(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Appairage automatique - Étape 3: Prêt et envoi de commande."""
        from .coordinator import RFXCOMCoordinator
        from . import DOMAIN as RFXCOM_DOMAIN
        import asyncio
        
        if not hasattr(self, '_pairing_data'):
            return await self.async_step_pair_device()
        
        protocol = self._pairing_data["protocol"]
        name = self._pairing_data["name"]
        
        lighting1_protocols = [
            PROTOCOL_X10, PROTOCOL_ARC, PROTOCOL_ABICOD, PROTOCOL_WAVEMAN,
            PROTOCOL_EMW100, PROTOCOL_IMPULS, PROTOCOL_RISINGSUN,
            PROTOCOL_PHILIPS, PROTOCOL_ENERGENIE, PROTOCOL_ENERGENIE_5,
            PROTOCOL_COCOSTICK
        ]
        
        if user_input is None:
            schema = vol.Schema({
                vol.Required("ready", default=False): bool,
            })
            return self.async_show_form(
                step_id="pair_device_ready",
                data_schema=schema,
                description_placeholders={
                    "instructions": (
                        f"**Protocole** : {protocol}\n"
                        f"**Nom** : {name}\n\n"
                        "**Étapes** :\n"
                        "1. Mettez votre appareil en mode appairage (suivez les instructions du fabricant)\n"
                        "2. Cochez la case ci-dessous quand l'appareil est prêt\n"
                        "3. Le système enverra une commande et détectera automatiquement l'appareil"
                    ),
                },
            )
        
        if not user_input.get("ready"):
            # L'utilisateur n'a pas coché la case
            schema = vol.Schema({
                vol.Required("ready", default=False): bool,
            })
            return self.async_show_form(
                step_id="pair_device_ready",
                data_schema=schema,
                errors={"base": "pairing_not_ready"},
                description_placeholders={
                    "instructions": (
                        f"**Protocole** : {protocol}\n"
                        f"**Nom** : {name}\n\n"
                        "**Étapes** :\n"
                        "1. Mettez votre appareil en mode appairage (suivez les instructions du fabricant)\n"
                        "2. Cochez la case ci-dessous quand l'appareil est prêt\n"
                        "3. Le système enverra une commande et détectera automatiquement l'appareil"
                    ),
                },
            )
        
        # Étape 4: Envoyer la commande d'appairage et attendre la réponse
        # Récupérer le coordinateur
        coordinator: RFXCOMCoordinator = self.hass.data[RFXCOM_DOMAIN][self.config_entry.entry_id]
        
        # Activer temporairement l'auto-registry si ce n'est pas déjà fait
        original_auto_registry = coordinator.auto_registry
        if not original_auto_registry:
            coordinator.auto_registry = True
            _LOGGER.info("Auto-registry activé temporairement pour l'appairage")
        
        try:
            # Envoyer la commande ON
            if protocol in lighting1_protocols:
                success = await coordinator.send_command(
                    protocol=protocol,
                    device_id="",
                    command=CMD_ON,
                    house_code=self._pairing_data["house_code"],
                    unit_code=self._pairing_data["unit_code"],
                )
            else:
                success = await coordinator.send_command(
                    protocol=protocol,
                    device_id=self._pairing_data["device_id"],
                    command=CMD_ON,
                )
            
            if not success:
                # Restaurer l'auto-registry
                coordinator.auto_registry = original_auto_registry
                return self.async_show_form(
                    step_id="pair_device_ready",
                    data_schema=vol.Schema({
                        vol.Required("ready", default=False): bool,
                    }),
                    errors={"base": "pairing_command_failed"},
                    description_placeholders={
                        "instructions": (
                            "Erreur lors de l'envoi de la commande d'appairage. "
                            "Vérifiez la connexion RFXCOM et réessayez."
                        ),
                    },
                )
            
            # Attendre une éventuelle réponse pendant quelques secondes
            # Note: En mode appairage, l'appareil ne répond pas toujours avec un paquet RFXCOM
            # Si la commande a été envoyée avec succès, l'appairage est considéré comme réussi
            _LOGGER.info("⏳ Attente d'une éventuelle réponse de l'appareil (max 5 secondes)...")
            
            # Attendre qu'un nouvel appareil soit détecté (optionnel)
            start_time = asyncio.get_event_loop().time()
            detected_device = None
            wait_timeout = min(5, PAIRING_TIMEOUT)  # Attendre max 5 secondes pour une réponse
            
            while (asyncio.get_event_loop().time() - start_time) < wait_timeout:
                await asyncio.sleep(0.5)  # Vérifier toutes les 0.5 secondes
                
                # Vérifier si un nouvel appareil a été détecté
                for unique_id, device_info in coordinator._discovered_devices.items():
                    if device_info.get(CONF_PROTOCOL) == protocol:
                        # Vérifier si c'est le bon appareil selon le protocole
                        if protocol in lighting1_protocols:
                            if (device_info.get(CONF_HOUSE_CODE) == self._pairing_data["house_code"] and
                                device_info.get(CONF_UNIT_CODE) == self._pairing_data["unit_code"]):
                                detected_device = device_info
                                _LOGGER.info("✅ Réponse de l'appareil détectée : %s", detected_device)
                                break
                        else:
                            if device_info.get(CONF_DEVICE_ID) == self._pairing_data["device_id"]:
                                detected_device = device_info
                                _LOGGER.info("✅ Réponse de l'appareil détectée : %s", detected_device)
                                break
                
                if detected_device:
                    break
            
            # Restaurer l'auto-registry
            coordinator.auto_registry = original_auto_registry
            
            # Si pas de réponse, ce n'est pas grave : l'appairage RFXCOM fonctionne ainsi
            # L'appareil s'appaire quand on envoie la commande, même sans réponse
            if not detected_device:
                _LOGGER.info(
                    "ℹ️ Aucune réponse de l'appareil, mais l'appairage est considéré comme réussi "
                    "(la commande a été envoyée avec succès)"
                )
            
            # Créer la configuration de l'appareil avec les codes/ID générés
            devices = self.config_entry.options.get("devices", [])
            device_type = self._pairing_data.get("device_type", DEVICE_TYPE_SWITCH)
            device_config = {
                "name": name,
                CONF_PROTOCOL: protocol,
                "device_type": device_type,
            }
            
            if protocol in lighting1_protocols:
                device_config[CONF_HOUSE_CODE] = self._pairing_data["house_code"]
                device_config[CONF_UNIT_CODE] = self._pairing_data["unit_code"]
                _LOGGER.info(
                    "✅ Appareil appairé : %s (protocole=%s, house_code=%s, unit_code=%s)",
                    name,
                    protocol,
                    self._pairing_data["house_code"],
                    self._pairing_data["unit_code"],
                )
            else:
                device_config[CONF_DEVICE_ID] = self._pairing_data["device_id"]
                if "unit_code" in self._pairing_data:
                    device_config[CONF_UNIT_CODE] = self._pairing_data["unit_code"]
                _LOGGER.info(
                    "✅ Appareil appairé : %s (protocole=%s, device_id=%s)",
                    name,
                    protocol,
                    self._pairing_data["device_id"],
                )
            
            devices.append(device_config)
            
            # Mettre à jour les options
            options = dict(self.config_entry.options)
            options["devices"] = devices
            
            # Mettre à jour l'entrée et recharger
            self.hass.config_entries.async_update_entry(
                self.config_entry, options=options
            )
            
            # Recharger l'intégration pour créer la nouvelle entité
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            
            return self.async_create_entry(title="", data=options)
            
        except Exception as err:
            _LOGGER.error("Erreur lors de l'appairage : %s", err)
            # Restaurer l'auto-registry
            coordinator.auto_registry = original_auto_registry
            return self.async_show_form(
                step_id="pair_device_ready",
                data_schema=vol.Schema({
                    vol.Required("ready", default=False): bool,
                }),
                errors={"base": "pairing_error"},
                description_placeholders={
                    "instructions": f"Erreur : {str(err)}",
                },
            )

    async def async_step_edit_device(
        self, device_idx: int | dict[str, Any] | None = None, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Modifie un appareil existant."""
        # Gérer le cas où device_idx est passé comme user_input (appel direct depuis Home Assistant)
        if isinstance(device_idx, dict):
            # Si device_idx est un dict, c'est en fait user_input qui a été passé
            # Cela signifie que device_idx n'a pas été fourni, on doit l'extraire d'ailleurs
            # Ce cas ne devrait pas arriver avec __getattr__, mais on le gère pour sécurité
            return await self.async_step_init()
        
        devices = self.config_entry.options.get("devices", [])
        if not isinstance(device_idx, int) or device_idx >= len(devices):
            return await self.async_step_init()

        device = devices[device_idx]

        # Récupérer les protocoles activés depuis les options
        enabled_protocols = self.config_entry.options.get(
            CONF_ENABLED_PROTOCOLS,
            []
        )
        
        if user_input is None:
            # Pré-remplir le formulaire avec les valeurs existantes
            protocol_options = enabled_protocols
            current_device_type = device.get("device_type", DEVICE_TYPE_SWITCH)
            schema_dict = {
                vol.Required("name", default=device.get("name")): str,
                vol.Required(CONF_PROTOCOL, default=device.get(CONF_PROTOCOL)): vol.In(protocol_options),
            }
            # Ajouter device_type seulement si ce n'est pas TEMP_HUM
            if device.get(CONF_PROTOCOL) != PROTOCOL_TEMP_HUM:
                schema_dict[vol.Optional("device_type", default=current_device_type)] = vol.In(["switch", "cover"])
            schema_dict[vol.Optional(CONF_DEVICE_ID, default=device.get(CONF_DEVICE_ID, ""))] = str
            schema_dict[vol.Optional(CONF_HOUSE_CODE, default=device.get(CONF_HOUSE_CODE, ""))] = str
            schema_dict[vol.Optional(CONF_UNIT_CODE, default=device.get(CONF_UNIT_CODE, ""))] = str
            schema = vol.Schema(schema_dict)
            return self.async_show_form(
                step_id="edit_device", data_schema=schema
            )

        # Mettre à jour l'appareil
        protocol = user_input[CONF_PROTOCOL]
        old_name = device.get("name")
        device["name"] = user_input["name"]
        device[CONF_PROTOCOL] = protocol
        
        # Sauvegarder le device_type si fourni (sauf pour TEMP_HUM qui est toujours sensor)
        if protocol != PROTOCOL_TEMP_HUM:
            device_type = user_input.get("device_type", device.get("device_type", DEVICE_TYPE_SWITCH))
            device["device_type"] = device_type
        else:
            device["device_type"] = DEVICE_TYPE_SENSOR
        
        _LOGGER.info(
            "Modification de l'appareil [%d]: ancien nom=%s, nouveau nom=%s, protocol=%s, device_type=%s",
            device_idx,
            old_name,
            device["name"],
            protocol,
            device.get("device_type"),
        )

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
        
        _LOGGER.info("Liste des appareils après modification (%d appareils):", len(devices))
        for idx, dev in enumerate(devices):
            _LOGGER.info("  [%d] %s (protocol=%s, device_type=%s)", idx, dev.get("name"), dev.get(CONF_PROTOCOL), dev.get("device_type"))

        # Mettre à jour les options (fusionner avec les options existantes)
        options = dict(self.config_entry.options)
        options["devices"] = devices
        
        # Mettre à jour l'entrée d'abord pour sauvegarder les options
        self.hass.config_entries.async_update_entry(
            self.config_entry, options=options
        )
        
        # Mettre à jour le device registry avec le nouveau nom
        from homeassistant.helpers import device_registry as dr
        device_registry = dr.async_get(self.hass)
        
        # Construire le device_identifier comme dans switch.py
        protocol = device.get(CONF_PROTOCOL, "")
        device_id = device.get(CONF_DEVICE_ID)
        house_code = device.get(CONF_HOUSE_CODE)
        unit_code = device.get(CONF_UNIT_CODE)
        
        if device_id:
            device_identifier = f"{protocol}_{device_id}_{device_idx}"
        elif house_code and unit_code:
            device_identifier = f"{protocol}_{house_code}_{unit_code}_{device_idx}"
        else:
            name_slug = device.get("name", "unknown").lower().replace(" ", "_")
            device_identifier = f"{protocol}_{name_slug}_{device_idx}"
        
        # Mettre à jour le device dans le device registry
        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, device_identifier)}
        )
        if device_entry:
            device_registry.async_update_device(
                device_entry.id,
                name=device.get("name", "Sans nom"),
            )
            _LOGGER.debug("Device registry mis à jour pour: %s", device.get("name"))
        
        # Recharger l'intégration pour mettre à jour les entités
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        
        return self.async_create_entry(title="", data=options)

    async def async_step_delete_device(
        self, device_idx: int | dict[str, Any] | None = None, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Supprime un appareil."""
        # Gérer le cas où device_idx est passé comme user_input (appel direct depuis Home Assistant)
        if isinstance(device_idx, dict):
            # Si device_idx est un dict, c'est en fait user_input qui a été passé
            # Cela signifie que device_idx n'a pas été fourni, on doit l'extraire d'ailleurs
            # Ce cas ne devrait pas arriver avec __getattr__, mais on le gère pour sécurité
            return await self.async_step_init()
        
        devices = self.config_entry.options.get("devices", [])
        if not isinstance(device_idx, int) or device_idx >= len(devices):
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
            device_to_delete = devices[device_idx]
            devices.pop(device_idx)
            
            # Mettre à jour les options (fusionner avec les options existantes)
            options = dict(self.config_entry.options)
            options["devices"] = devices
            
            # Mettre à jour l'entrée d'abord pour sauvegarder les options
            self.hass.config_entries.async_update_entry(
                self.config_entry, options=options
            )
            
            # Supprimer le device du device registry
            from homeassistant.helpers import device_registry as dr
            device_registry = dr.async_get(self.hass)
            
            # Construire le device_identifier comme dans switch.py
            protocol = device_to_delete.get(CONF_PROTOCOL, "")
            device_id = device_to_delete.get(CONF_DEVICE_ID)
            house_code = device_to_delete.get(CONF_HOUSE_CODE)
            unit_code = device_to_delete.get(CONF_UNIT_CODE)
            
            if device_id:
                device_identifier = f"{protocol}_{device_id}_{device_idx}"
            elif house_code and unit_code:
                device_identifier = f"{protocol}_{house_code}_{unit_code}_{device_idx}"
            else:
                name_slug = device_to_delete.get("name", "unknown").lower().replace(" ", "_")
                device_identifier = f"{protocol}_{name_slug}_{device_idx}"
            
            # Supprimer le device du device registry (cela supprimera aussi les entités associées)
            device_entry = device_registry.async_get_device(
                identifiers={(DOMAIN, device_identifier)}
            )
            if device_entry:
                device_registry.async_remove_device(device_entry.id)
                _LOGGER.debug("Device supprimé du device registry: %s", device_identifier)
            
            # Recharger l'intégration pour supprimer l'entité
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            
            return self.async_create_entry(title="", data=options)

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

