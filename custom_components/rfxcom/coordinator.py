"""Coordinateur pour la communication RFXCOM."""
from __future__ import annotations

import asyncio
import logging
import serial
import socket
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DEFAULT_BAUDRATE,
    DEFAULT_PORT,
    DEFAULT_HOST,
    DEFAULT_NETWORK_PORT,
    CONNECTION_TYPE_USB,
    CONNECTION_TYPE_NETWORK,
    PROTOCOL_AC,
    PROTOCOL_ARC,
    PROTOCOL_TEMP_HUM,
    CMD_ON,
    CMD_OFF,
    PACKET_TYPE_LIGHTING1,
    PACKET_TYPE_TEMP_HUM,
    SUBTYPE_ARC,
    SUBTYPE_TH13,
    CONF_AUTO_REGISTRY,
    DEFAULT_AUTO_REGISTRY,
    CONF_PROTOCOL,
    CONF_HOUSE_CODE,
    CONF_UNIT_CODE,
    CONF_DEVICE_ID,
)

_LOGGER = logging.getLogger(__name__)


class RFXCOMCoordinator(DataUpdateCoordinator):
    """Coordinateur pour gérer la communication RFXCOM."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise le coordinateur RFXCOM."""
        super().__init__(
            hass,
            _LOGGER,
            name="RFXCOM",
            update_interval=None,
        )
        self.hass = hass
        self.entry = entry
        self.serial_port: serial.Serial | None = None
        self.socket: socket.socket | None = None
        self.connection_type = entry.data.get("connection_type", CONNECTION_TYPE_USB)
        self.port = entry.data.get("port", DEFAULT_PORT)
        self.baudrate = entry.data.get("baudrate", DEFAULT_BAUDRATE)
        self.host = entry.data.get("host", DEFAULT_HOST)
        self.network_port = entry.data.get("network_port", DEFAULT_NETWORK_PORT)
        # auto_registry peut être dans data (configuration initiale) ou options (modification)
        self.auto_registry = entry.data.get(CONF_AUTO_REGISTRY) or entry.options.get(CONF_AUTO_REGISTRY, DEFAULT_AUTO_REGISTRY)
        self._sequence_number = 0
        self._lock = asyncio.Lock()
        self._receive_task: asyncio.Task | None = None
        self._discovered_devices: dict[str, dict[str, Any]] = {}

    async def async_setup(self) -> None:
        """Configure la connexion USB ou réseau."""
        try:
            if self.connection_type == CONNECTION_TYPE_USB:
                _LOGGER.debug("Configuration connexion USB: port=%s, baudrate=%s", self.port, self.baudrate)
                self.serial_port = await self.hass.async_add_executor_job(
                    serial.Serial,
                    self.port,
                    self.baudrate,
                )
                self.serial_port.timeout = 1
                self.serial_port.write_timeout = 1
                _LOGGER.info("Connexion RFXCOM USB établie sur %s", self.port)
                _LOGGER.debug("Port série configuré: timeout=1s, write_timeout=1s")
            elif self.connection_type == CONNECTION_TYPE_NETWORK:
                _LOGGER.debug("Configuration connexion réseau: host=%s, port=%s", self.host, self.network_port)
                self.socket = await self.hass.async_add_executor_job(
                    socket.socket,
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                )
                await self.hass.async_add_executor_job(
                    self.socket.connect,
                    (self.host, self.network_port),
                )
                _LOGGER.info(
                    "Connexion RFXCOM réseau établie sur %s:%s",
                    self.host,
                    self.network_port,
                )
                _LOGGER.debug("Socket réseau connectée avec succès")
            else:
                raise ValueError(f"Type de connexion inconnu: {self.connection_type}")
            
            # Démarrer la réception de messages si auto-registry est activé
            if self.auto_registry:
                _LOGGER.debug("Auto-registry activé, démarrage de la boucle de réception")
                self._receive_task = asyncio.create_task(self._async_receive_loop())
                _LOGGER.info("Mode auto-registry activé - Détection automatique des appareils")
            else:
                _LOGGER.debug("Auto-registry désactivé, pas de réception de messages")
        except Exception as err:
            _LOGGER.error("Erreur lors de la connexion RFXCOM: %s", err)
            raise

    async def async_shutdown(self) -> None:
        """Ferme la connexion."""
        # Arrêter la tâche de réception
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self.connection_type == CONNECTION_TYPE_USB:
            if self.serial_port and self.serial_port.is_open:
                await self.hass.async_add_executor_job(self.serial_port.close)
                _LOGGER.info("Connexion RFXCOM USB fermée")
        elif self.connection_type == CONNECTION_TYPE_NETWORK:
            if self.socket:
                await self.hass.async_add_executor_job(self.socket.close)
                _LOGGER.info("Connexion RFXCOM réseau fermée")

    async def send_command(
        self,
        protocol: str,
        device_id: str,
        command: str,
        house_code: str | None = None,
        unit_code: str | None = None,
    ) -> bool:
        """Envoie une commande RFXCOM."""
        _LOGGER.debug(
            "Envoi commande: protocole=%s, device_id=%s, command=%s, house_code=%s, unit_code=%s",
            protocol,
            device_id,
            command,
            house_code,
            unit_code,
        )
        async with self._lock:
            # Vérifier la connexion
            if self.connection_type == CONNECTION_TYPE_USB:
                if not self.serial_port or not self.serial_port.is_open:
                    _LOGGER.error("Le port série n'est pas ouvert")
                    return False
                _LOGGER.debug("Port série vérifié: ouvert=%s", self.serial_port.is_open)
            elif self.connection_type == CONNECTION_TYPE_NETWORK:
                if not self.socket:
                    _LOGGER.error("La socket réseau n'est pas ouverte")
                    return False
                _LOGGER.debug("Socket réseau vérifiée: présente=%s", self.socket is not None)

            try:
                # Construction de la commande selon le protocole
                if protocol == PROTOCOL_AC:
                    _LOGGER.debug("Construction commande AC: device_id=%s", device_id)
                    cmd_bytes = self._build_ac_command(device_id, command)
                elif protocol == PROTOCOL_ARC:
                    _LOGGER.debug(
                        "Construction commande ARC: house_code=%s, unit_code=%s",
                        house_code,
                        unit_code,
                    )
                    cmd_bytes = self._build_arc_command(
                        house_code, unit_code, command
                    )
                else:
                    _LOGGER.error("Protocole non supporté: %s", protocol)
                    return False
                
                _LOGGER.debug("Commande construite: %s bytes, hex=%s", len(cmd_bytes), cmd_bytes.hex())

                # Envoi de la commande
                if self.connection_type == CONNECTION_TYPE_USB:
                    await self.hass.async_add_executor_job(
                        self.serial_port.write, cmd_bytes
                    )
                    await self.hass.async_add_executor_job(
                        self.serial_port.flush
                    )
                elif self.connection_type == CONNECTION_TYPE_NETWORK:
                    await self.hass.async_add_executor_job(
                        self.socket.sendall, cmd_bytes
                    )

                _LOGGER.debug(
                    "Commande envoyée: protocole=%s, device=%s, commande=%s, bytes=%s",
                    protocol,
                    device_id or f"{house_code}/{unit_code}",
                    command,
                    cmd_bytes.hex(),
                )
                return True

            except Exception as err:
                _LOGGER.error("Erreur lors de l'envoi de la commande: %s", err)
                return False

    def _build_ac_command(self, device_id: str, command: str) -> bytes:
        """Construit une commande AC."""
        # Convertir l'ID de l'appareil en bytes (8 bytes)
        device_bytes = self._hex_string_to_bytes(device_id, 8)
        
        # Commande AC: 0x0B (longueur) + 0x10 (type AC) + 8 bytes device + 1 byte command
        cmd_byte = 0x01 if command == CMD_ON else 0x00
        
        return bytes([0x0B, 0x10, 0x00]) + device_bytes + bytes([cmd_byte])

    def _build_arc_command(
        self, house_code: str | None, unit_code: str | None, command: str
    ) -> bytes:
        """Construit une commande ARC selon le format RFXCOM.
        
        Format: 07 10 01 62 41 01 01 00
        - 07: longueur
        - 10: Lighting1
        - 01: subtype ARC
        - 62: sequence number
        - 41: house code (A = 0x41)
        - 01: unit code
        - 01: command (ON=0x01, OFF=0x00)
        - 00: signal level
        """
        # Incrémenter le numéro de séquence
        old_seq = self._sequence_number
        self._sequence_number = (self._sequence_number + 1) % 256
        _LOGGER.debug(
            "ARC command: house_code=%s, unit_code=%s, command=%s, sequence=%s->%s",
            house_code,
            unit_code,
            command,
            old_seq,
            self._sequence_number,
        )
        
        # Convertir house code (A=0x41, B=0x42, etc.)
        if house_code:
            if len(house_code) == 1 and house_code.isalpha():
                hc = ord(house_code.upper())  # A = 0x41, B = 0x42, etc.
            else:
                try:
                    hc = int(house_code, 16) if house_code.startswith("0x") else int(house_code)
                except ValueError:
                    hc = 0x41  # Default to A
        else:
            hc = 0x41  # Default to A
        
        # Convertir unit code
        try:
            uc = int(unit_code) if unit_code else 1
        except (ValueError, TypeError):
            uc = 1
        
        # Commande
        cmd_byte = 0x01 if command == CMD_ON else 0x00
        
        # Construire le paquet: 07 10 01 [seq] [house] [unit] [cmd] 00
        return bytes([
            0x07,  # Longueur
            PACKET_TYPE_LIGHTING1,  # 0x10 Lighting1
            SUBTYPE_ARC,  # 0x01 ARC
            self._sequence_number,  # Sequence number
            hc,  # House code
            uc,  # Unit code
            cmd_byte,  # Command
            0x00,  # Signal level
        ])

    def _hex_string_to_bytes(self, hex_str: str, length: int) -> bytes:
        """Convertit une chaîne hexadécimale en bytes."""
        try:
            # Supprimer les espaces et les séparateurs
            hex_str = hex_str.replace(" ", "").replace(":", "").replace("-", "")
            
            # Convertir en bytes
            device_bytes = bytes.fromhex(hex_str)
            
            # Compléter ou tronquer à la longueur souhaitée
            if len(device_bytes) < length:
                device_bytes = device_bytes + bytes(length - len(device_bytes))
            elif len(device_bytes) > length:
                device_bytes = device_bytes[:length]
            
            return device_bytes
        except ValueError:
            _LOGGER.error("Erreur lors de la conversion hex: %s", hex_str)
            return bytes(length)

    async def _async_receive_loop(self) -> None:
        """Boucle de réception des messages RFXCOM."""
        _LOGGER.info("Démarrage de la réception des messages RFXCOM")
        _LOGGER.debug("Type de connexion: %s", self.connection_type)
        
        while True:
            try:
                # Lire les données
                if self.connection_type == CONNECTION_TYPE_USB:
                    if not self.serial_port or not self.serial_port.is_open:
                        _LOGGER.debug("Port série fermé, attente...")
                        await asyncio.sleep(1)
                        continue
                    
                    # Lire la longueur du paquet (premier byte)
                    data = await self.hass.async_add_executor_job(
                        self.serial_port.read, 1
                    )
                    if not data or len(data) < 1:
                        await asyncio.sleep(0.1)
                        continue
                    
                    packet_length = data[0]
                    _LOGGER.debug("Paquet reçu: longueur=%s", packet_length)
                    if packet_length < 1 or packet_length > 50:
                        _LOGGER.debug("Longueur invalide, ignoré: %s", packet_length)
                        continue
                    
                    # Lire le reste du paquet
                    remaining = await self.hass.async_add_executor_job(
                        self.serial_port.read, packet_length - 1
                    )
                    if len(remaining) < packet_length - 1:
                        _LOGGER.debug("Paquet incomplet: reçu %s/%s bytes", len(remaining), packet_length - 1)
                        continue
                    
                    packet = data + remaining
                    _LOGGER.debug("Paquet complet reçu: %s bytes, hex=%s", len(packet), packet.hex())
                    
                elif self.connection_type == CONNECTION_TYPE_NETWORK:
                    if not self.socket:
                        _LOGGER.debug("Socket fermée, attente...")
                        await asyncio.sleep(1)
                        continue
                    
                    # Lire la longueur
                    data = await self.hass.async_add_executor_job(
                        self.socket.recv, 1
                    )
                    if not data or len(data) < 1:
                        await asyncio.sleep(0.1)
                        continue
                    
                    packet_length = data[0]
                    _LOGGER.debug("Paquet réseau reçu: longueur=%s", packet_length)
                    if packet_length < 1 or packet_length > 50:
                        _LOGGER.debug("Longueur invalide, ignoré: %s", packet_length)
                        continue
                    
                    # Lire le reste
                    remaining = await self.hass.async_add_executor_job(
                        self.socket.recv, packet_length - 1
                    )
                    if len(remaining) < packet_length - 1:
                        _LOGGER.debug("Paquet incomplet: reçu %s/%s bytes", len(remaining), packet_length - 1)
                        continue
                    
                    packet = data + remaining
                    _LOGGER.debug("Paquet réseau complet: %s bytes, hex=%s", len(packet), packet.hex())
                else:
                    await asyncio.sleep(1)
                    continue
                
                # Parser le paquet
                _LOGGER.debug("Parsing du paquet: %s", packet.hex())
                device_info = self._parse_packet(packet)
                if device_info:
                    _LOGGER.debug("Appareil parsé: %s", device_info)
                    await self._handle_discovered_device(device_info)
                else:
                    _LOGGER.debug("Paquet non reconnu ou ignoré")
                    
            except asyncio.CancelledError:
                _LOGGER.info("Réception des messages RFXCOM arrêtée")
                break
            except Exception as err:
                _LOGGER.error("Erreur lors de la réception: %s", err)
                await asyncio.sleep(1)

    def _parse_packet(self, packet: bytes) -> dict[str, Any] | None:
        """Parse un paquet RFXCOM et extrait les informations de l'appareil."""
        if len(packet) < 4:
            _LOGGER.debug("Paquet trop court: %s bytes (minimum 4)", len(packet))
            return None
        
        packet_type = packet[1]
        _LOGGER.debug("Type de paquet: 0x%02X", packet_type)
        
        # Lighting1 / ARC
        if packet_type == PACKET_TYPE_LIGHTING1 and len(packet) >= 8:
            subtype = packet[2]
            _LOGGER.debug("Subtype: 0x%02X", subtype)
            if subtype == SUBTYPE_ARC:
                house_code_byte = packet[4]
                unit_code = packet[5]
                command = packet[6]
                
                _LOGGER.debug(
                    "ARC paquet: house_code_byte=0x%02X, unit_code=%s, command=0x%02X",
                    house_code_byte,
                    unit_code,
                    command,
                )
                
                # Convertir house code byte en lettre
                house_code = chr(house_code_byte) if 0x41 <= house_code_byte <= 0x50 else None
                
                if house_code:
                    device_info = {
                        CONF_PROTOCOL: PROTOCOL_ARC,
                        CONF_HOUSE_CODE: house_code,
                        CONF_UNIT_CODE: str(unit_code),
                        "command": CMD_ON if command == 0x01 else CMD_OFF,
                        "raw_packet": packet.hex(),
                    }
                    _LOGGER.debug("ARC appareil détecté: %s", device_info)
                    return device_info
                else:
                    _LOGGER.debug("House code invalide: 0x%02X", house_code_byte)
        
        # AC protocol (format: 0x0B 0x10 0x00 [8 bytes device] [1 byte command])
        elif packet_type == 0x10 and len(packet) >= 12:
            # Vérifier si c'est AC (pas ARC)
            if len(packet) == 12:
                device_id_bytes = packet[3:11]
                device_id = device_id_bytes.hex()
                command_byte = packet[11]
                
                _LOGGER.debug(
                    "AC paquet: device_id=%s, command=0x%02X",
                    device_id,
                    command_byte,
                )
                
                device_info = {
                    CONF_PROTOCOL: PROTOCOL_AC,
                    CONF_DEVICE_ID: device_id,
                    "command": CMD_ON if command_byte == 0x01 else CMD_OFF,
                    "raw_packet": packet.hex(),
                }
                _LOGGER.debug("AC appareil détecté: %s", device_info)
                return device_info
            else:
                _LOGGER.debug("Paquet type 0x10 mais longueur incorrecte: %s (attendu 12)", len(packet))
        
        # TEMP_HUM protocol (format: 0x0A 0x52 0x0D [seq] [id(2)] [temp(2)] [hum(1)] [status(1)] [signal(1)])
        # Exemple: 0A520D35680300D4270289
        # 0A=longueur, 52=TEMP_HUM, 0D=TH13, 35=seq, 6803=ID, 00D4=temp, 27=hum, 02=status, 89=signal/battery
        elif packet_type == PACKET_TYPE_TEMP_HUM and len(packet) >= 11:
            subtype = packet[2]
            _LOGGER.debug("TEMP_HUM subtype: 0x%02X", subtype)
            
            if subtype == SUBTYPE_TH13:  # TH13 - Alecto WS1700
                # ID: bytes 4-5 (big-endian: 0x6803 = 26627)
                device_id_int = (packet[4] << 8) | packet[5]
                device_id = str(device_id_int)
                
                # Température: bytes 6-7 (big-endian, en dixièmes de degré: 0x00D4 = 212 = 21.2°C)
                temp_raw = (packet[6] << 8) | packet[7]
                # Gérer les températures négatives (si bit de signe)
                if temp_raw & 0x8000:
                    temperature = ((temp_raw ^ 0xFFFF) + 1) / -10.0
                else:
                    temperature = temp_raw / 10.0
                
                # Humidité: byte 8 (0x27 = 39%)
                humidity = packet[8]
                
                # Status: byte 9 (0x02 = Dry)
                status_byte = packet[9]
                status_map = {
                    0x00: "Normal",
                    0x01: "Comfort",
                    0x02: "Dry",
                    0x03: "Wet",
                }
                status = status_map.get(status_byte, f"Unknown(0x{status_byte:02X})")
                
                # Signal level et Battery: byte 10 (0x89 = signal=8, battery=9)
                signal_level = (packet[10] >> 4) & 0x0F
                battery_nibble = packet[10] & 0x0F
                battery_ok = battery_nibble == 0x09  # 9 = OK, autres = LOW
                
                _LOGGER.debug(
                    "TEMP_HUM paquet: device_id=%s, temp=%.1f°C, hum=%s%%, status=%s, signal=%s, battery=%s",
                    device_id,
                    temperature,
                    humidity,
                    status,
                    signal_level,
                    "OK" if battery_ok else "LOW",
                )
                
                device_info = {
                    CONF_PROTOCOL: PROTOCOL_TEMP_HUM,
                    CONF_DEVICE_ID: device_id,
                    "temperature": temperature,
                    "humidity": humidity,
                    "status": status,
                    "signal_level": signal_level,
                    "battery_ok": battery_ok,
                    "subtype": "TH13",
                    "raw_packet": packet.hex(),
                }
                _LOGGER.debug("TEMP_HUM appareil détecté: %s", device_info)
                return device_info
            else:
                _LOGGER.debug("TEMP_HUM subtype non supporté: 0x%02X", subtype)
        else:
            _LOGGER.debug("Type de paquet non reconnu: 0x%02X, longueur=%s", packet_type, len(packet))
        
        return None

    async def _handle_discovered_device(self, device_info: dict[str, Any]) -> None:
        """Gère un appareil découvert."""
        # Créer un identifiant unique
        if device_info[CONF_PROTOCOL] == PROTOCOL_ARC:
            device_id = f"{device_info[CONF_HOUSE_CODE]}_{device_info[CONF_UNIT_CODE]}"
        elif device_info[CONF_PROTOCOL] == PROTOCOL_TEMP_HUM:
            device_id = device_info[CONF_DEVICE_ID]
        else:
            device_id = device_info[CONF_DEVICE_ID]
        
        unique_id = f"{device_info[CONF_PROTOCOL]}_{device_id}"
        _LOGGER.debug("Identifiant unique généré: %s", unique_id)
        
        # Mettre à jour les données si l'appareil est déjà connu (pour les capteurs)
        if unique_id in self._discovered_devices:
            _LOGGER.debug("Appareil déjà connu, mise à jour des données: %s", unique_id)
            # Mettre à jour les données (important pour les capteurs qui envoient régulièrement)
            old_data = self._discovered_devices[unique_id]
            old_data.update(device_info)
            # Notifier les entités du changement
            self.async_update_listeners()
            return
        
        # Enregistrer l'appareil découvert
        self._discovered_devices[unique_id] = device_info
        _LOGGER.debug("Appareil ajouté au cache: %s", unique_id)
        
        _LOGGER.info(
            "Nouvel appareil détecté: %s - %s",
            device_info[CONF_PROTOCOL],
            device_id,
        )
        
        # Si auto-registry est activé, ajouter automatiquement
        if self.auto_registry:
            _LOGGER.debug("Auto-registry activé, enregistrement automatique...")
            await self._auto_register_device(device_info, unique_id)
        else:
            _LOGGER.debug("Auto-registry désactivé, appareil non enregistré automatiquement")

    async def _auto_register_device(
        self, device_info: dict[str, Any], unique_id: str
    ) -> None:
        """Enregistre automatiquement un appareil découvert."""
        try:
            _LOGGER.debug("Début auto-enregistrement: %s", unique_id)
            # Récupérer les appareils existants
            devices = self.entry.options.get("devices", [])
            _LOGGER.debug("Appareils existants: %s", len(devices))
            
            # Vérifier si l'appareil existe déjà
            for existing in devices:
                if device_info[CONF_PROTOCOL] == PROTOCOL_ARC:
                    if (
                        existing.get(CONF_HOUSE_CODE) == device_info[CONF_HOUSE_CODE]
                        and existing.get(CONF_UNIT_CODE) == device_info[CONF_UNIT_CODE]
                    ):
                        _LOGGER.debug("Appareil ARC déjà enregistré: %s/%s", device_info[CONF_HOUSE_CODE], device_info[CONF_UNIT_CODE])
                        return  # Déjà enregistré
                elif device_info[CONF_PROTOCOL] == PROTOCOL_TEMP_HUM:
                    if existing.get(CONF_DEVICE_ID) == device_info[CONF_DEVICE_ID]:
                        _LOGGER.debug("Appareil TEMP_HUM déjà enregistré: %s", device_info[CONF_DEVICE_ID])
                        return  # Déjà enregistré
                else:
                    if existing.get(CONF_DEVICE_ID) == device_info[CONF_DEVICE_ID]:
                        _LOGGER.debug("Appareil AC déjà enregistré: %s", device_info[CONF_DEVICE_ID])
                        return  # Déjà enregistré
            
            # Créer la configuration du nouvel appareil
            protocol = device_info[CONF_PROTOCOL]
            if protocol == PROTOCOL_TEMP_HUM:
                device_name = f"RFXCOM Temp/Hum {device_info[CONF_DEVICE_ID]}"
            else:
                device_name = f"RFXCOM {protocol} {unique_id.split('_', 1)[1]}"
            
            device_config = {
                "name": device_name,
                CONF_PROTOCOL: protocol,
            }
            
            if protocol == PROTOCOL_ARC:
                device_config[CONF_HOUSE_CODE] = device_info[CONF_HOUSE_CODE]
                device_config[CONF_UNIT_CODE] = device_info[CONF_UNIT_CODE]
            elif protocol == PROTOCOL_TEMP_HUM:
                device_config[CONF_DEVICE_ID] = device_info[CONF_DEVICE_ID]
                # Stocker les données du capteur pour les entités sensor
                device_config["sensor_data"] = {
                    "temperature": device_info.get("temperature"),
                    "humidity": device_info.get("humidity"),
                    "status": device_info.get("status"),
                    "signal_level": device_info.get("signal_level"),
                    "battery_ok": device_info.get("battery_ok"),
                }
            else:
                device_config[CONF_DEVICE_ID] = device_info[CONF_DEVICE_ID]
            
            # Ajouter l'appareil
            devices.append(device_config)
            _LOGGER.debug("Configuration auto-enregistrée: %s", device_config)
            
            # Mettre à jour les options
            _LOGGER.debug("Mise à jour des options avec %s appareils", len(devices))
            self.hass.config_entries.async_update_entry(
                self.entry, options={"devices": devices}
            )
            
            _LOGGER.info(
                "Appareil auto-enregistré: %s",
                device_config["name"],
            )
            
            # Recharger l'intégration pour créer la nouvelle entité
            _LOGGER.debug("Rechargement de l'intégration pour créer la nouvelle entité")
            await self.hass.config_entries.async_reload(self.entry.entry_id)
            
        except Exception as err:
            _LOGGER.error("Erreur lors de l'auto-enregistrement: %s", err)

    def get_discovered_devices(self) -> list[dict[str, Any]]:
        """Retourne la liste des appareils découverts."""
        return list(self._discovered_devices.values())

