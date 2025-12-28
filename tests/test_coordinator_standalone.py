"""Tests unitaires pour le coordinateur RFXCOM (sans Home Assistant)."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

# Mock minimal de Home Assistant
class MockHass:
    def __init__(self):
        self.async_add_executor_job = AsyncMock()

class MockConfigEntry:
    def __init__(self, data):
        self.data = data
        self.entry_id = "test_entry"

# Import après les mocks
import sys
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()

# Mock DataUpdateCoordinator
class MockDataUpdateCoordinator:
    def __init__(self, hass, logger, name, update_interval):
        pass

sys.modules['homeassistant.helpers.update_coordinator'].DataUpdateCoordinator = MockDataUpdateCoordinator

# Maintenant on peut importer
from custom_components.rfxcom.coordinator import RFXCOMCoordinator
from custom_components.rfxcom.const import PROTOCOL_ARC, PROTOCOL_AC, CMD_ON, CMD_OFF, CONNECTION_TYPE_USB, CONNECTION_TYPE_NETWORK


@pytest.fixture
def mock_hass():
    """Mock Home Assistant."""
    return MockHass()


@pytest.fixture
def mock_entry_usb():
    """Mock ConfigEntry USB."""
    return MockConfigEntry({
        "port": "/dev/ttyUSB0",
        "baudrate": 38400,
        "connection_type": CONNECTION_TYPE_USB,
    })


@pytest.fixture
def mock_entry_network():
    """Mock ConfigEntry réseau."""
    return MockConfigEntry({
        "connection_type": CONNECTION_TYPE_NETWORK,
        "host": "192.168.1.100",
        "network_port": 10001,
    })


@pytest.fixture
def coordinator_usb(mock_hass, mock_entry_usb):
    """Créer un coordinateur USB pour les tests."""
    return RFXCOMCoordinator(mock_hass, mock_entry_usb)


@pytest.fixture
def coordinator_network(mock_hass, mock_entry_network):
    """Créer un coordinateur réseau pour les tests."""
    return RFXCOMCoordinator(mock_hass, mock_entry_network)


class TestRFXCOMCoordinator:
    """Tests pour RFXCOMCoordinator."""

    @pytest.mark.asyncio
    async def test_setup_usb(self, coordinator_usb, mock_hass):
        """Test de la configuration USB."""
        with patch("serial.Serial") as mock_serial:
            mock_port = MagicMock()
            mock_port.is_open = True
            mock_serial.return_value = mock_port
            mock_hass.async_add_executor_job = AsyncMock(return_value=mock_port)
            await coordinator_usb.async_setup()
            assert coordinator_usb.serial_port is not None

    @pytest.mark.asyncio
    async def test_setup_network(self, coordinator_network, mock_hass):
        """Test de la configuration réseau."""
        with patch("socket.socket") as mock_socket_class:
            mock_sock = MagicMock()
            mock_socket_class.return_value = mock_sock
            mock_hass.async_add_executor_job = AsyncMock(side_effect=[
                mock_sock,  # socket.socket()
                None,  # socket.connect()
            ])
            await coordinator_network.async_setup()
            assert coordinator_network.socket is not None

    @pytest.mark.asyncio
    async def test_shutdown_usb(self, coordinator_usb):
        """Test de la fermeture USB."""
        coordinator_usb.serial_port = MagicMock()
        coordinator_usb.serial_port.is_open = True
        coordinator_usb.connection_type = CONNECTION_TYPE_USB
        coordinator_usb.hass.async_add_executor_job = AsyncMock()
        await coordinator_usb.async_shutdown()
        assert coordinator_usb.hass.async_add_executor_job.called

    @pytest.mark.asyncio
    async def test_shutdown_network(self, coordinator_network):
        """Test de la fermeture réseau."""
        coordinator_network.socket = MagicMock()
        coordinator_network.connection_type = CONNECTION_TYPE_NETWORK
        coordinator_network.hass.async_add_executor_job = AsyncMock()
        await coordinator_network.async_shutdown()
        assert coordinator_network.hass.async_add_executor_job.called

    def test_build_arc_command_on(self, coordinator_usb):
        """Test de construction d'une commande ARC ON."""
        cmd = coordinator_usb._build_arc_command("A", "1", CMD_ON)
        
        assert len(cmd) == 8
        assert cmd[0] == 0x07  # Longueur
        assert cmd[1] == 0x10  # Lighting1
        assert cmd[2] == 0x01  # ARC subtype
        assert cmd[4] == 0x41  # House code A
        assert cmd[5] == 0x01  # Unit code 1
        assert cmd[6] == 0x01  # Command ON

    def test_build_arc_command_off(self, coordinator_usb):
        """Test de construction d'une commande ARC OFF."""
        cmd = coordinator_usb._build_arc_command("A", "1", CMD_OFF)
        
        assert len(cmd) == 8
        assert cmd[6] == 0x00  # Command OFF

    def test_build_arc_command_house_codes(self, coordinator_usb):
        """Test de conversion des house codes."""
        # House code A = 0x41
        cmd = coordinator_usb._build_arc_command("A", "1", CMD_ON)
        assert cmd[4] == 0x41
        
        # House code B = 0x42
        cmd = coordinator_usb._build_arc_command("B", "1", CMD_ON)
        assert cmd[4] == 0x42
        
        # House code P = 0x50
        cmd = coordinator_usb._build_arc_command("P", "1", CMD_ON)
        assert cmd[4] == 0x50

    def test_build_arc_command_unit_codes(self, coordinator_usb):
        """Test de conversion des unit codes."""
        for unit in range(1, 17):
            cmd = coordinator_usb._build_arc_command("A", str(unit), CMD_ON)
            assert cmd[5] == unit

    def test_build_arc_command_sequence_number(self, coordinator_usb):
        """Test de l'incrémentation du sequence number."""
        cmd1 = coordinator_usb._build_arc_command("A", "1", CMD_ON)
        seq1 = cmd1[3]
        
        cmd2 = coordinator_usb._build_arc_command("A", "1", CMD_ON)
        seq2 = cmd2[3]
        
        assert seq2 == (seq1 + 1) % 256

    def test_build_ac_command(self, coordinator_usb):
        """Test de construction d'une commande AC."""
        device_id = "0102030405060708"
        cmd = coordinator_usb._build_ac_command(device_id, CMD_ON)
        
        assert len(cmd) == 12  # 0x0B + 0x10 + 0x00 + 8 bytes device + 1 byte command
        assert cmd[0] == 0x0B  # Longueur
        assert cmd[1] == 0x10  # Type AC
        assert cmd[-1] == 0x01  # Command ON

    def test_hex_string_to_bytes(self, coordinator_usb):
        """Test de conversion hexadécimale."""
        # Test avec espaces
        result = coordinator_usb._hex_string_to_bytes("01 02 03 04", 4)
        assert result == bytes([0x01, 0x02, 0x03, 0x04])
        
        # Test sans espaces
        result = coordinator_usb._hex_string_to_bytes("01020304", 4)
        assert result == bytes([0x01, 0x02, 0x03, 0x04])
        
        # Test avec séparateurs
        result = coordinator_usb._hex_string_to_bytes("01:02:03:04", 4)
        assert result == bytes([0x01, 0x02, 0x03, 0x04])
        
        # Test avec padding
        result = coordinator_usb._hex_string_to_bytes("01", 4)
        assert len(result) == 4
        assert result[0] == 0x01
        assert result[1:] == bytes([0x00, 0x00, 0x00])
        
        # Test avec troncature
        result = coordinator_usb._hex_string_to_bytes("0102030405060708", 4)
        assert len(result) == 4
        assert result == bytes([0x01, 0x02, 0x03, 0x04])

    def test_hex_string_to_bytes_invalid(self, coordinator_usb):
        """Test de conversion hexadécimale invalide."""
        result = coordinator_usb._hex_string_to_bytes("invalid", 4)
        assert len(result) == 4
        assert result == bytes([0x00, 0x00, 0x00, 0x00])

    @pytest.mark.asyncio
    async def test_send_command_arc_usb(self, coordinator_usb, mock_hass):
        """Test d'envoi de commande ARC via USB."""
        coordinator_usb.serial_port = MagicMock()
        coordinator_usb.serial_port.is_open = True
        coordinator_usb.serial_port.write = Mock()
        coordinator_usb.serial_port.flush = Mock()
        
        mock_hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
        
        result = await coordinator_usb.send_command(
            PROTOCOL_ARC, "", CMD_ON, house_code="A", unit_code="1"
        )
        
        assert result is True
        assert coordinator_usb.serial_port.write.called
        assert coordinator_usb.serial_port.flush.called

    @pytest.mark.asyncio
    async def test_send_command_arc_network(self, coordinator_network, mock_hass):
        """Test d'envoi de commande ARC via réseau."""
        coordinator_network.socket = MagicMock()
        coordinator_network.socket.sendall = Mock()
        
        mock_hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
        
        result = await coordinator_network.send_command(
            PROTOCOL_ARC, "", CMD_ON, house_code="A", unit_code="1"
        )
        
        assert result is True
        assert coordinator_network.socket.sendall.called

    @pytest.mark.asyncio
    async def test_send_command_port_closed(self, coordinator_usb):
        """Test d'envoi avec port fermé."""
        coordinator_usb.serial_port = None
        
        result = await coordinator_usb.send_command(
            PROTOCOL_ARC, "", CMD_ON, house_code="A", unit_code="1"
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_socket_closed(self, coordinator_network):
        """Test d'envoi avec socket fermée."""
        coordinator_network.socket = None
        
        result = await coordinator_network.send_command(
            PROTOCOL_ARC, "", CMD_ON, house_code="A", unit_code="1"
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_unsupported_protocol(self, coordinator_usb, mock_hass):
        """Test d'envoi avec protocole non supporté."""
        coordinator_usb.serial_port = MagicMock()
        coordinator_usb.serial_port.is_open = True
        
        result = await coordinator_usb.send_command(
            "UNSUPPORTED", "", CMD_ON
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_exception(self, coordinator_usb, mock_hass):
        """Test d'envoi avec exception."""
        coordinator_usb.serial_port = MagicMock()
        coordinator_usb.serial_port.is_open = True
        coordinator_usb.serial_port.write = Mock(side_effect=Exception("Test error"))
        
        mock_hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
        
        result = await coordinator_usb.send_command(
            PROTOCOL_ARC, "", CMD_ON, house_code="A", unit_code="1"
        )
        
        assert result is False


