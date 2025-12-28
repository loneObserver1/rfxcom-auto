"""Tests étendus pour coordinator.py pour augmenter la couverture."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

from custom_components.rfxcom.coordinator import RFXCOMCoordinator
from custom_components.rfxcom.const import (
    PROTOCOL_AC,
    PROTOCOL_ARC,
    PROTOCOL_TEMP_HUM,
    CMD_ON,
    CMD_OFF,
    CONNECTION_TYPE_USB,
    CONNECTION_TYPE_NETWORK,
    PACKET_TYPE_LIGHTING1,
    PACKET_TYPE_LIGHTING2,
    PACKET_TYPE_TEMP_HUM,
    SUBTYPE_ARC,
    SUBTYPE_AC,
    SUBTYPE_TH13,
    CONF_AUTO_REGISTRY,
)


@pytest.fixture
def mock_hass():
    """Mock de Home Assistant."""
    hass = MagicMock()
    
    async def async_add_executor_job(func, *args):
        """Simule async_add_executor_job."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args)
        return func(*args)
    
    hass.async_add_executor_job = async_add_executor_job
    return hass


@pytest.fixture
def mock_entry_usb():
    """Mock d'une entrée de configuration USB."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.data = {
        "connection_type": CONNECTION_TYPE_USB,
        "port": "/dev/ttyUSB0",
        "baudrate": 38400,
    }
    entry.options = MagicMock()
    entry.options.get = Mock(return_value=False)  # auto_registry désactivé
    return entry


@pytest.fixture
def mock_entry_network():
    """Mock d'une entrée de configuration réseau."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.data = {
        "connection_type": CONNECTION_TYPE_NETWORK,
        "host": "localhost",
        "network_port": 8889,
    }
    entry.options = MagicMock()
    entry.options.get = Mock(return_value=False)
    return entry


class TestCoordinatorExtended:
    """Tests étendus pour le coordinator."""

    @pytest.mark.asyncio
    async def test_setup_usb_connection(self, mock_hass, mock_entry_usb):
        """Test de configuration USB."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        
        with patch("serial.Serial", return_value=mock_serial):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
            await coordinator.async_setup()
        
        assert coordinator.serial_port is not None
        assert coordinator.connection_type == CONNECTION_TYPE_USB

    @pytest.mark.asyncio
    async def test_setup_network_connection(self, mock_hass, mock_entry_network):
        """Test de configuration réseau."""
        mock_socket = MagicMock()
        mock_socket.getpeername = Mock(return_value=("localhost", 8889))
        
        with patch("socket.socket", return_value=mock_socket):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_network)
            await coordinator.async_setup()
        
        assert coordinator.socket is not None
        assert coordinator.connection_type == CONNECTION_TYPE_NETWORK

    @pytest.mark.asyncio
    async def test_send_command_lighting1(self, mock_hass, mock_entry_usb):
        """Test d'envoi de commande Lighting1."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        with patch("serial.Serial", return_value=mock_serial):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
            await coordinator.async_setup()
            
            result = await coordinator.send_command(
                protocol=PROTOCOL_ARC,
                device_id="",
                command=CMD_ON,
                house_code="A",
                unit_code="1",
            )
        
        assert result is True
        assert mock_serial.write.called

    @pytest.mark.asyncio
    async def test_send_command_lighting2_python(self, mock_hass, mock_entry_usb):
        """Test d'envoi de commande Lighting2 avec Python (fallback)."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        with patch("serial.Serial", return_value=mock_serial):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
            coordinator._use_node_bridge = False  # Désactiver Node.js
            await coordinator.async_setup()
            
            result = await coordinator.send_command(
                protocol=PROTOCOL_AC,
                device_id="02382C82",
                command=CMD_ON,
                unit_code="2",
            )
        
        assert result is True
        assert mock_serial.write.called

    @pytest.mark.asyncio
    async def test_send_command_lighting3(self, mock_hass, mock_entry_usb):
        """Test d'envoi de commande Lighting3."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        with patch("serial.Serial", return_value=mock_serial):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
            await coordinator.async_setup()
            
            result = await coordinator.send_command(
                protocol="IKEA_KOPPLA",
                device_id="010203",
                command=CMD_ON,
                unit_code="1",
            )
        
        assert result is True
        assert mock_serial.write.called

    @pytest.mark.asyncio
    async def test_send_command_lighting4(self, mock_hass, mock_entry_usb):
        """Test d'envoi de commande Lighting4."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        with patch("serial.Serial", return_value=mock_serial):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
            await coordinator.async_setup()
            
            result = await coordinator.send_command(
                protocol="PT2262",
                device_id="010203",
                command=CMD_ON,
            )
        
        assert result is True
        assert mock_serial.write.called

    @pytest.mark.asyncio
    async def test_send_command_lighting5(self, mock_hass, mock_entry_usb):
        """Test d'envoi de commande Lighting5."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        with patch("serial.Serial", return_value=mock_serial):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
            await coordinator.async_setup()
            
            result = await coordinator.send_command(
                protocol="LIGHTWAVERF",
                device_id="010203",
                command=CMD_ON,
                unit_code="1",
            )
        
        assert result is True
        assert mock_serial.write.called

    @pytest.mark.asyncio
    async def test_send_command_lighting6(self, mock_hass, mock_entry_usb):
        """Test d'envoi de commande Lighting6."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        with patch("serial.Serial", return_value=mock_serial):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
            await coordinator.async_setup()
            
            result = await coordinator.send_command(
                protocol="BLYSS",
                device_id="0102",
                command=CMD_ON,
            )
        
        assert result is True
        assert mock_serial.write.called

    @pytest.mark.asyncio
    async def test_send_command_network(self, mock_hass, mock_entry_network):
        """Test d'envoi de commande via réseau."""
        mock_socket = MagicMock()
        mock_socket.getpeername = Mock(return_value=("localhost", 8889))
        mock_socket.sendall = Mock()
        
        with patch("socket.socket", return_value=mock_socket):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_network)
            await coordinator.async_setup()
            
            result = await coordinator.send_command(
                protocol=PROTOCOL_ARC,
                device_id="",
                command=CMD_ON,
                house_code="A",
                unit_code="1",
            )
        
        assert result is True
        assert mock_socket.sendall.called

    @pytest.mark.asyncio
    async def test_send_command_unsupported_protocol(self, mock_hass, mock_entry_usb):
        """Test d'envoi avec protocole non supporté."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        
        with patch("serial.Serial", return_value=mock_serial):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
            await coordinator.async_setup()
            
            result = await coordinator.send_command(
                protocol="UNKNOWN",
                device_id="",
                command=CMD_ON,
            )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_port_closed(self, mock_hass, mock_entry_usb):
        """Test d'envoi avec port fermé."""
        mock_serial = MagicMock()
        mock_serial.is_open = False
        
        with patch("serial.Serial", return_value=mock_serial):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
            coordinator.serial_port = mock_serial
            await coordinator.async_setup()
            
            result = await coordinator.send_command(
                protocol=PROTOCOL_ARC,
                device_id="",
                command=CMD_ON,
                house_code="A",
                unit_code="1",
            )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_usb(self, mock_hass, mock_entry_usb):
        """Test de fermeture USB."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.close = Mock()
        
        with patch("serial.Serial", return_value=mock_serial):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
            await coordinator.async_setup()
            await coordinator.async_shutdown()
        
        assert mock_serial.close.called

    @pytest.mark.asyncio
    async def test_shutdown_network(self, mock_hass, mock_entry_network):
        """Test de fermeture réseau."""
        mock_socket = MagicMock()
        mock_socket.getpeername = Mock(return_value=("localhost", 8889))
        mock_socket.close = Mock()
        
        with patch("socket.socket", return_value=mock_socket):
            coordinator = RFXCOMCoordinator(mock_hass, mock_entry_network)
            await coordinator.async_setup()
            await coordinator.async_shutdown()
        
        assert mock_socket.close.called

    def test_build_lighting1_command_off(self, mock_hass, mock_entry_usb):
        """Test de construction de commande Lighting1 OFF."""
        coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
        
        cmd = coordinator._build_lighting1_command(
            PROTOCOL_ARC, SUBTYPE_ARC, "A", "1", CMD_OFF
        )
        
        assert len(cmd) == 8
        assert cmd[1] == PACKET_TYPE_LIGHTING1
        assert cmd[7] == 0x00  # OFF command (dernier byte)

    def test_build_lighting2_command_with_unit_code(self, mock_hass, mock_entry_usb):
        """Test de construction de commande Lighting2 avec unit_code."""
        coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
        
        cmd = coordinator._build_lighting2_command(
            PROTOCOL_AC, SUBTYPE_AC, "02382C82", CMD_ON, unit_code=2
        )
        
        assert len(cmd) == 12
        assert cmd[1] == PACKET_TYPE_LIGHTING2
        assert cmd[8] == 2  # Unit code
        assert cmd[9] == 0x01  # ON command

    def test_hex_string_to_bytes_padding(self, mock_hass, mock_entry_usb):
        """Test de conversion hex avec padding."""
        coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
        
        # Test avec chaîne courte
        result = coordinator._hex_string_to_bytes("01", 4)
        assert len(result) == 4
        assert result == bytes([0x00, 0x00, 0x00, 0x01])

    def test_hex_string_to_bytes_truncate(self, mock_hass, mock_entry_usb):
        """Test de conversion hex avec troncature."""
        coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
        
        # Test avec chaîne longue
        result = coordinator._hex_string_to_bytes("010203040506", 4)
        assert len(result) == 4
        # Devrait garder les 4 derniers bytes (LSB) - les 6 bytes sont 01 02 03 04 05 06
        # Tronqués à 4 bytes: 03 04 05 06
        assert result == bytes([0x03, 0x04, 0x05, 0x06])

    def test_hex_string_to_bytes_odd_length(self, mock_hass, mock_entry_usb):
        """Test de conversion hex avec longueur impaire."""
        coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
        
        # Test avec chaîne de longueur impaire
        result = coordinator._hex_string_to_bytes("123", 2)
        assert len(result) == 2
        assert result == bytes([0x01, 0x23])

    def test_get_discovered_devices(self, mock_hass, mock_entry_usb):
        """Test de récupération des appareils découverts."""
        coordinator = RFXCOMCoordinator(mock_hass, mock_entry_usb)
        
        # Ajouter un appareil découvert
        coordinator._discovered_devices["test"] = {
            "protocol": PROTOCOL_TEMP_HUM,
            "device_id": "6803",
        }
        
        devices = coordinator.get_discovered_devices()
        assert len(devices) == 1
        assert devices[0]["device_id"] == "6803"

