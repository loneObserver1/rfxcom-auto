"""Tests pour le coordinateur RFXCOM."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

from custom_components.rfxcom.coordinator import RFXCOMCoordinator
from custom_components.rfxcom.const import PROTOCOL_ARC, PROTOCOL_AC, CMD_ON, CMD_OFF


@pytest.fixture
def mock_hass():
    """Mock Home Assistant."""
    hass = Mock()
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def mock_entry():
    """Mock ConfigEntry."""
    entry = Mock()
    entry.data = {
        "port": "/dev/ttyUSB0",
        "baudrate": 38400,
        "connection_type": "usb",
    }
    entry.entry_id = "test_entry"
    return entry


@pytest.fixture
def coordinator(mock_hass, mock_entry):
    """Créer un coordinateur pour les tests."""
    return RFXCOMCoordinator(mock_hass, mock_entry)


class TestRFXCOMCoordinator:
    """Tests pour RFXCOMCoordinator."""

    @pytest.mark.asyncio
    async def test_setup_usb(self, coordinator, mock_hass):
        """Test de la configuration USB."""
        with patch("serial.Serial") as mock_serial:
            mock_serial.return_value.is_open = True
            await coordinator.async_setup()
            assert coordinator.serial_port is not None
            mock_serial.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_network(self, mock_hass):
        """Test de la configuration réseau."""
        entry = Mock()
        entry.data = {
            "connection_type": "network",
            "host": "192.168.1.100",
            "network_port": 10001,
        }
        entry.entry_id = "test_entry"
        coordinator = RFXCOMCoordinator(mock_hass, entry)
        
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            await coordinator.async_setup()
            assert coordinator.socket is not None
            mock_sock.connect.assert_called_once_with(("192.168.1.100", 10001))

    @pytest.mark.asyncio
    async def test_shutdown(self, coordinator):
        """Test de la fermeture."""
        coordinator.serial_port = Mock()
        coordinator.serial_port.is_open = True
        await coordinator.async_shutdown()
        coordinator.serial_port.close.assert_called_once()

    def test_build_arc_command_on(self, coordinator):
        """Test de construction d'une commande ARC ON."""
        # Format attendu: 07 10 01 62 41 01 01 00
        # 07 = longueur, 10 = Lighting1, 01 = ARC, 62 = seq, 41 = house A, 01 = unit, 01 = ON, 00 = signal
        cmd = coordinator._build_arc_command("A", "1", CMD_ON)
        
        assert len(cmd) == 8
        assert cmd[0] == 0x07  # Longueur
        assert cmd[1] == 0x10  # Lighting1
        assert cmd[2] == 0x01  # ARC subtype
        assert cmd[4] == 0x41  # House code A
        assert cmd[5] == 0x01  # Unit code 1
        assert cmd[6] == 0x01  # Command ON

    def test_build_arc_command_off(self, coordinator):
        """Test de construction d'une commande ARC OFF."""
        cmd = coordinator._build_arc_command("A", "1", CMD_OFF)
        
        assert len(cmd) == 8
        assert cmd[6] == 0x00  # Command OFF

    def test_build_arc_command_house_code_conversion(self, coordinator):
        """Test de conversion du house code."""
        # House code A = 0x41
        cmd = coordinator._build_arc_command("A", "1", CMD_ON)
        assert cmd[4] == 0x41
        
        # House code B = 0x42
        cmd = coordinator._build_arc_command("B", "1", CMD_ON)
        assert cmd[4] == 0x42

    def test_hex_string_to_bytes(self, coordinator):
        """Test de conversion hexadécimale."""
        # Test avec espaces
        result = coordinator._hex_string_to_bytes("01 02 03 04", 4)
        assert result == bytes([0x01, 0x02, 0x03, 0x04])
        
        # Test sans espaces
        result = coordinator._hex_string_to_bytes("01020304", 4)
        assert result == bytes([0x01, 0x02, 0x03, 0x04])
        
        # Test avec séparateurs
        result = coordinator._hex_string_to_bytes("01:02:03:04", 4)
        assert result == bytes([0x01, 0x02, 0x03, 0x04])
        
        # Test avec padding
        result = coordinator._hex_string_to_bytes("01", 4)
        assert len(result) == 4
        assert result[0] == 0x01

    @pytest.mark.asyncio
    async def test_send_command_arc(self, coordinator, mock_hass):
        """Test d'envoi de commande ARC."""
        coordinator.serial_port = Mock()
        coordinator.serial_port.is_open = True
        coordinator.serial_port.write = Mock()
        coordinator.serial_port.flush = Mock()
        
        mock_hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
        
        result = await coordinator.send_command(
            PROTOCOL_ARC, "", CMD_ON, house_code="A", unit_code="1"
        )
        
        assert result is True
        assert coordinator.serial_port.write.called
        assert coordinator.serial_port.flush.called

    @pytest.mark.asyncio
    async def test_send_command_port_closed(self, coordinator):
        """Test d'envoi avec port fermé."""
        coordinator.serial_port = None
        
        result = await coordinator.send_command(
            PROTOCOL_ARC, "", CMD_ON, house_code="A", unit_code="1"
        )
        
        assert result is False


