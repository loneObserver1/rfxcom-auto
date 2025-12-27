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
    CMD_ON,
    CMD_OFF,
    PACKET_TYPE_LIGHTING1,
    SUBTYPE_ARC,
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
        self._sequence_number = 0
        self._lock = asyncio.Lock()

    async def async_setup(self) -> None:
        """Configure la connexion USB ou réseau."""
        try:
            if self.connection_type == CONNECTION_TYPE_USB:
                self.serial_port = await self.hass.async_add_executor_job(
                    serial.Serial,
                    self.port,
                    self.baudrate,
                )
                self.serial_port.timeout = 1
                self.serial_port.write_timeout = 1
                _LOGGER.info("Connexion RFXCOM USB établie sur %s", self.port)
            elif self.connection_type == CONNECTION_TYPE_NETWORK:
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
            else:
                raise ValueError(f"Type de connexion inconnu: {self.connection_type}")
        except Exception as err:
            _LOGGER.error("Erreur lors de la connexion RFXCOM: %s", err)
            raise

    async def async_shutdown(self) -> None:
        """Ferme la connexion."""
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
        async with self._lock:
            # Vérifier la connexion
            if self.connection_type == CONNECTION_TYPE_USB:
                if not self.serial_port or not self.serial_port.is_open:
                    _LOGGER.error("Le port série n'est pas ouvert")
                    return False
            elif self.connection_type == CONNECTION_TYPE_NETWORK:
                if not self.socket:
                    _LOGGER.error("La socket réseau n'est pas ouverte")
                    return False

            try:
                # Construction de la commande selon le protocole
                if protocol == PROTOCOL_AC:
                    cmd_bytes = self._build_ac_command(device_id, command)
                elif protocol == PROTOCOL_ARC:
                    cmd_bytes = self._build_arc_command(
                        house_code, unit_code, command
                    )
                else:
                    _LOGGER.error("Protocole non supporté: %s", protocol)
                    return False

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
        self._sequence_number = (self._sequence_number + 1) % 256
        
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

