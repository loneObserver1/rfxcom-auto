"""Coordinateur pour la communication RFXCOM."""
from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any

import serial

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
    PROTOCOL_TO_PACKET,
    CMD_ON,
    CMD_OFF,
    PACKET_TYPE_LIGHTING1,
    PACKET_TYPE_LIGHTING2,
    PACKET_TYPE_LIGHTING3,
    PACKET_TYPE_LIGHTING4,
    PACKET_TYPE_LIGHTING5,
    PACKET_TYPE_LIGHTING6,
    PACKET_TYPE_TEMP_HUM,
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
                if protocol not in PROTOCOL_TO_PACKET:
                    _LOGGER.error("Protocole non supporté: %s", protocol)
                    return False

                packet_type, subtype = PROTOCOL_TO_PACKET[protocol]
                _LOGGER.debug(
                    "Construction commande %s: packet_type=0x%02X, subtype=%s",
                    protocol,
                    packet_type,
                    subtype,
                )

                # Construire la commande selon le type de paquet
                if packet_type == PACKET_TYPE_LIGHTING1:
                    cmd_bytes = self._build_lighting1_command(
                        protocol, subtype, house_code, unit_code, command
                    )
                elif packet_type == PACKET_TYPE_LIGHTING2:
                    cmd_bytes = self._build_lighting2_command(
                        protocol, subtype, device_id, command
                    )
                elif packet_type == PACKET_TYPE_LIGHTING3:
                    cmd_bytes = self._build_lighting3_command(
                        protocol, device_id, unit_code, command
                    )
                elif packet_type == PACKET_TYPE_LIGHTING4:
                    cmd_bytes = self._build_lighting4_command(
                        protocol, device_id, command
                    )
                elif packet_type == PACKET_TYPE_LIGHTING5:
                    cmd_bytes = self._build_lighting5_command(
                        protocol, subtype, device_id, unit_code, command
                    )
                elif packet_type == PACKET_TYPE_LIGHTING6:
                    cmd_bytes = self._build_lighting6_command(
                        protocol, device_id, command
                    )
                else:
                    _LOGGER.error("Type de paquet non supporté: 0x%02X", packet_type)
                    return False

                if not cmd_bytes:
                    _LOGGER.error("Échec de la construction de la commande pour %s", protocol)
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

    def _build_lighting1_command(
        self,
        protocol: str,
        subtype: int,
        house_code: str | None,
        unit_code: str | None,
        command: str,
    ) -> bytes:
        """Construit une commande Lighting1 (X10, ARC, ABICOD, etc.).

        Format: [length] 0x10 [subtype] [seq] [house] [unit] [cmd] [signal]
        """
        # Incrémenter le numéro de séquence
        self._sequence_number = (self._sequence_number + 1) % 256

        # Convertir house code (A=0x41, B=0x42, etc. ou hex)
        hc = 0x41  # Default to A
        if house_code:
            if len(house_code) == 1 and house_code.isalpha():
                hc = ord(house_code.upper())
            else:
                try:
                    hc = int(house_code, 16) if house_code.startswith("0x") else int(house_code)
                except ValueError:
                    pass

        # Convertir unit code
        try:
            uc = int(unit_code) if unit_code else 1
        except (ValueError, TypeError):
            uc = 1

        # Commande
        cmd_byte = 0x01 if command == CMD_ON else 0x00

        # Construire le paquet: 07 10 [subtype] [seq] [house] [unit] [cmd] 00
        return bytes([
            0x07,  # Longueur
            PACKET_TYPE_LIGHTING1,  # 0x10
            subtype,
            self._sequence_number,
            hc,
            uc,
            cmd_byte,
            0x00,  # Signal level
        ])

    def _build_lighting2_command(
        self,
        protocol: str,
        subtype: int,
        device_id: str | None,
        command: str,
    ) -> bytes:
        """Construit une commande Lighting2 (AC, HomeEasy EU, etc.).

        Format: [length] 0x11 [subtype] [id(4)] [unit] [cmd] [level] [signal]
        """
        # Incrémenter le numéro de séquence
        self._sequence_number = (self._sequence_number + 1) % 256

        # Convertir device_id en 4 bytes
        device_bytes = self._hex_string_to_bytes(device_id or "00000000", 4)

        # Unit code (généralement 0 pour AC)
        unit_code = 0

        # Commande
        cmd_byte = 0x01 if command == CMD_ON else 0x00

        # Level (0x0F = 100% pour ON, 0x00 pour OFF)
        level = 0x0F if command == CMD_ON else 0x00

        # Construire le paquet: 0B 11 [subtype] [id(4)] [unit] [cmd] [level] 00
        return bytes([
            0x0B,  # Longueur
            PACKET_TYPE_LIGHTING2,  # 0x11
            subtype,
            self._sequence_number,
        ]) + device_bytes + bytes([
            unit_code,
            cmd_byte,
            level,
            0x00,  # Signal level
        ])

    def _build_lighting3_command(
        self,
        protocol: str,
        device_id: str | None,
        unit_code: str | None,
        command: str,
    ) -> bytes:
        """Construit une commande Lighting3 (Ikea Koppla).

        Format: [length] 0x12 [id(2)] [group] [unit] [cmd] [signal]
        """
        # Incrémenter le numéro de séquence
        self._sequence_number = (self._sequence_number + 1) % 256

        # Convertir device_id en 2 bytes
        device_bytes = self._hex_string_to_bytes(device_id or "0000", 2)

        # Group (généralement 0)
        group = 0

        # Unit code
        try:
            uc = int(unit_code) if unit_code else 1
        except (ValueError, TypeError):
            uc = 1

        # Commande
        cmd_byte = 0x01 if command == CMD_ON else 0x00

        # Construire le paquet: 08 12 [id(2)] [group] [unit] [cmd] 00
        return bytes([
            0x08,  # Longueur
            PACKET_TYPE_LIGHTING3,  # 0x12
            self._sequence_number,
        ]) + device_bytes + bytes([
            group,
            uc,
            cmd_byte,
            0x00,  # Signal level
        ])

    def _build_lighting4_command(
        self,
        protocol: str,
        device_id: str | None,
        command: str,
    ) -> bytes:
        """Construit une commande Lighting4 (PT2262).

        Format: [length] 0x13 [id(3)] [cmd] [signal]
        """
        # Incrémenter le numéro de séquence
        self._sequence_number = (self._sequence_number + 1) % 256

        # Convertir device_id en 3 bytes
        device_bytes = self._hex_string_to_bytes(device_id or "000000", 3)

        # Commande
        cmd_byte = 0x01 if command == CMD_ON else 0x00

        # Construire le paquet: 07 13 [id(3)] [cmd] 00
        return bytes([
            0x07,  # Longueur
            PACKET_TYPE_LIGHTING4,  # 0x13
            self._sequence_number,
        ]) + device_bytes + bytes([
            cmd_byte,
            0x00,  # Signal level
        ])

    def _build_lighting5_command(
        self,
        protocol: str,
        subtype: int,
        device_id: str | None,
        unit_code: str | None,
        command: str,
    ) -> bytes:
        """Construit une commande Lighting5 (LightwaveRF, etc.).

        Format: [length] 0x14 [subtype] [id(3)] [unit] [cmd] [level] [signal]
        """
        # Incrémenter le numéro de séquence
        self._sequence_number = (self._sequence_number + 1) % 256

        # Convertir device_id en 3 bytes
        device_bytes = self._hex_string_to_bytes(device_id or "000000", 3)

        # Unit code
        try:
            uc = int(unit_code) if unit_code else 0
        except (ValueError, TypeError):
            uc = 0

        # Commande
        cmd_byte = 0x01 if command == CMD_ON else 0x00

        # Level (0x0F = 100% pour ON, 0x00 pour OFF)
        level = 0x0F if command == CMD_ON else 0x00

        # Construire le paquet: 0A 14 [subtype] [id(3)] [unit] [cmd] [level] 00
        return bytes([
            0x0A,  # Longueur
            PACKET_TYPE_LIGHTING5,  # 0x14
            subtype,
            self._sequence_number,
        ]) + device_bytes + bytes([
            uc,
            cmd_byte,
            level,
            0x00,  # Signal level
        ])

    def _build_lighting6_command(
        self,
        protocol: str,
        device_id: str | None,
        command: str,
    ) -> bytes:
        """Construit une commande Lighting6 (BLYSS).

        Format: [length] 0x15 [id(2)] [group] [unit] [cmd] [signal]
        """
        # Incrémenter le numéro de séquence
        self._sequence_number = (self._sequence_number + 1) % 256

        # Convertir device_id en 2 bytes
        device_bytes = self._hex_string_to_bytes(device_id or "0000", 2)

        # Group (généralement 0)
        group = 0

        # Unit code (généralement 0)
        unit_code = 0

        # Commande
        cmd_byte = 0x01 if command == CMD_ON else 0x00

        # Construire le paquet: 08 15 [id(2)] [group] [unit] [cmd] 00
        return bytes([
            0x08,  # Longueur
            PACKET_TYPE_LIGHTING6,  # 0x15
            self._sequence_number,
        ]) + device_bytes + bytes([
            group,
            unit_code,
            cmd_byte,
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

        # Lighting1 (X10, ARC, ABICOD, etc.)
        if packet_type == PACKET_TYPE_LIGHTING1 and len(packet) >= 8:
            return self._parse_lighting1_packet(packet)

        # Lighting2 (AC, HomeEasy EU, etc.)
        elif packet_type == PACKET_TYPE_LIGHTING2 and len(packet) >= 11:
            return self._parse_lighting2_packet(packet)

        # Lighting3 (Ikea Koppla)
        elif packet_type == PACKET_TYPE_LIGHTING3 and len(packet) >= 8:
            return self._parse_lighting3_packet(packet)

        # Lighting4 (PT2262)
        elif packet_type == PACKET_TYPE_LIGHTING4 and len(packet) >= 7:
            return self._parse_lighting4_packet(packet)

        # Lighting5 (LightwaveRF, etc.)
        elif packet_type == PACKET_TYPE_LIGHTING5 and len(packet) >= 10:
            return self._parse_lighting5_packet(packet)

        # Lighting6 (BLYSS)
        elif packet_type == PACKET_TYPE_LIGHTING6 and len(packet) >= 8:
            return self._parse_lighting6_packet(packet)

        # TEMP_HUM protocol
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

    def _parse_lighting1_packet(self, packet: bytes) -> dict[str, Any] | None:
        """Parse un paquet Lighting1 (X10, ARC, ABICOD, etc.)."""
        subtype = packet[2]
        house_code_byte = packet[4]
        unit_code = packet[5]
        command = packet[6]

        # Mapping subtype -> protocole
        subtype_to_protocol = {
            0x00: PROTOCOL_X10,
            0x01: PROTOCOL_ARC,
            0x02: PROTOCOL_ABICOD,
            0x03: PROTOCOL_WAVEMAN,
            0x04: PROTOCOL_EMW100,
            0x05: PROTOCOL_IMPULS,
            0x06: PROTOCOL_RISINGSUN,
            0x07: PROTOCOL_PHILIPS,
            0x08: PROTOCOL_ENERGENIE,
            0x09: PROTOCOL_ENERGENIE_5,
            0x0A: PROTOCOL_COCOSTICK,
        }

        protocol = subtype_to_protocol.get(subtype)
        if not protocol:
            _LOGGER.debug("Lighting1 subtype non supporté: 0x%02X", subtype)
            return None

        # Convertir house code byte en lettre (pour ARC et autres)
        house_code = None
        if 0x41 <= house_code_byte <= 0x50:
            house_code = chr(house_code_byte)
        else:
            house_code = f"0x{house_code_byte:02X}"

        device_info = {
            CONF_PROTOCOL: protocol,
            CONF_HOUSE_CODE: house_code,
            CONF_UNIT_CODE: str(unit_code),
            "command": CMD_ON if command == 0x01 else CMD_OFF,
            "raw_packet": packet.hex(),
        }
        _LOGGER.debug("%s appareil détecté: %s", protocol, device_info)
        return device_info

    def _parse_lighting2_packet(self, packet: bytes) -> dict[str, Any] | None:
        """Parse un paquet Lighting2 (AC, HomeEasy EU, etc.)."""
        subtype = packet[2]
        device_id_bytes = packet[4:8]
        device_id = device_id_bytes.hex()
        unit_code = packet[8]
        command = packet[9]

        # Mapping subtype -> protocole
        subtype_to_protocol = {
            0x00: PROTOCOL_AC,
            0x01: PROTOCOL_HOMEEASY_EU,
            0x02: PROTOCOL_ANSLUT,
            0x03: PROTOCOL_KAMBROOK,
        }

        protocol = subtype_to_protocol.get(subtype)
        if not protocol:
            _LOGGER.debug("Lighting2 subtype non supporté: 0x%02X", subtype)
            return None

        device_info = {
            CONF_PROTOCOL: protocol,
            CONF_DEVICE_ID: device_id,
            CONF_UNIT_CODE: str(unit_code),
            "command": CMD_ON if command == 0x01 else CMD_OFF,
            "raw_packet": packet.hex(),
        }
        _LOGGER.debug("%s appareil détecté: %s", protocol, device_info)
        return device_info

    def _parse_lighting3_packet(self, packet: bytes) -> dict[str, Any] | None:
        """Parse un paquet Lighting3 (Ikea Koppla)."""
        device_id_bytes = packet[3:5]
        device_id = device_id_bytes.hex()
        group = packet[5]
        unit_code = packet[6]
        command = packet[7]

        device_info = {
            CONF_PROTOCOL: PROTOCOL_IKEA_KOPPLA,
            CONF_DEVICE_ID: device_id,
            CONF_UNIT_CODE: str(unit_code),
            "group": str(group),
            "command": CMD_ON if command == 0x01 else CMD_OFF,
            "raw_packet": packet.hex(),
        }
        _LOGGER.debug("Ikea Koppla appareil détecté: %s", device_info)
        return device_info

    def _parse_lighting4_packet(self, packet: bytes) -> dict[str, Any] | None:
        """Parse un paquet Lighting4 (PT2262)."""
        device_id_bytes = packet[3:6]
        device_id = device_id_bytes.hex()
        command = packet[6]

        device_info = {
            CONF_PROTOCOL: PROTOCOL_PT2262,
            CONF_DEVICE_ID: device_id,
            "command": CMD_ON if command == 0x01 else CMD_OFF,
            "raw_packet": packet.hex(),
        }
        _LOGGER.debug("PT2262 appareil détecté: %s", device_info)
        return device_info

    def _parse_lighting5_packet(self, packet: bytes) -> dict[str, Any] | None:
        """Parse un paquet Lighting5 (LightwaveRF, etc.)."""
        subtype = packet[2]
        device_id_bytes = packet[4:7]
        device_id = device_id_bytes.hex()
        unit_code = packet[7]
        command = packet[8]

        # Mapping subtype -> protocole
        subtype_to_protocol = {
            0x00: PROTOCOL_LIGHTWAVERF,
            0x01: PROTOCOL_EMW100_GDO,
            0x02: PROTOCOL_BBSB,
            0x03: PROTOCOL_RSL,
            0x04: PROTOCOL_LIVOLO,
            0x05: PROTOCOL_TRC02,
            0x06: PROTOCOL_AOKE,
            0x07: PROTOCOL_RGB_TRC02,
        }

        protocol = subtype_to_protocol.get(subtype)
        if not protocol:
            _LOGGER.debug("Lighting5 subtype non supporté: 0x%02X", subtype)
            return None

        device_info = {
            CONF_PROTOCOL: protocol,
            CONF_DEVICE_ID: device_id,
            CONF_UNIT_CODE: str(unit_code),
            "command": CMD_ON if command == 0x01 else CMD_OFF,
            "raw_packet": packet.hex(),
        }
        _LOGGER.debug("%s appareil détecté: %s", protocol, device_info)
        return device_info

    def _parse_lighting6_packet(self, packet: bytes) -> dict[str, Any] | None:
        """Parse un paquet Lighting6 (BLYSS)."""
        device_id_bytes = packet[3:5]
        device_id = device_id_bytes.hex()
        group = packet[5]
        unit_code = packet[6]
        command = packet[7]

        device_info = {
            CONF_PROTOCOL: PROTOCOL_BLYSS,
            CONF_DEVICE_ID: device_id,
            CONF_UNIT_CODE: str(unit_code),
            "group": str(group),
            "command": CMD_ON if command == 0x01 else CMD_OFF,
            "raw_packet": packet.hex(),
        }
        _LOGGER.debug("BLYSS appareil détecté: %s", device_info)
        return device_info

    async def _handle_discovered_device(self, device_info: dict[str, Any]) -> None:
        """Gère un appareil découvert."""
        # Créer un identifiant unique selon le protocole
        protocol = device_info[CONF_PROTOCOL]
        if protocol in [PROTOCOL_ARC, PROTOCOL_X10, PROTOCOL_ABICOD, PROTOCOL_WAVEMAN,
                        PROTOCOL_EMW100, PROTOCOL_IMPULS, PROTOCOL_RISINGSUN,
                        PROTOCOL_PHILIPS, PROTOCOL_ENERGENIE, PROTOCOL_ENERGENIE_5,
                        PROTOCOL_COCOSTICK]:
            # Protocoles avec house_code/unit_code
            device_id = f"{device_info.get(CONF_HOUSE_CODE, '')}_{device_info.get(CONF_UNIT_CODE, '')}"
        elif protocol == PROTOCOL_TEMP_HUM:
            device_id = device_info[CONF_DEVICE_ID]
        else:
            # Protocoles avec device_id
            device_id = device_info.get(CONF_DEVICE_ID, "")

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

