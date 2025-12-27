"""Tests pour les méthodes du coordinateur avec mocks complets."""
import pytest
import sys
import os
import importlib.util
from unittest.mock import Mock, AsyncMock, MagicMock, patch

# Charger const directement
const_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'rfxcom', 'const.py')
spec = importlib.util.spec_from_file_location("const", const_path)
const = importlib.util.module_from_spec(spec)
spec.loader.exec_module(const)

# Mock Home Assistant avant d'importer coordinator
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

# Mock serial
sys.modules['serial'] = MagicMock()

# Maintenant charger coordinator
coordinator_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'rfxcom', 'coordinator.py')
spec = importlib.util.spec_from_file_location("coordinator", coordinator_path)
coordinator_module = importlib.util.module_from_spec(spec)

# Mock les imports avant d'exécuter
with patch('serial.Serial'), patch('socket.socket'):
    spec.loader.exec_module(coordinator_module)

RFXCOMCoordinator = coordinator_module.RFXCOMCoordinator


class MockHass:
    def __init__(self):
        self.async_add_executor_job = AsyncMock()


class MockEntry:
    def __init__(self, data):
        self.data = data
        self.entry_id = "test"


def test_coordinator_init_usb():
    """Test d'initialisation USB."""
    hass = MockHass()
    entry = MockEntry({
        "connection_type": const.CONNECTION_TYPE_USB,
        "port": "/dev/ttyUSB0",
        "baudrate": 38400,
    })
    
    coordinator = RFXCOMCoordinator(hass, entry)
    assert coordinator.connection_type == const.CONNECTION_TYPE_USB
    assert coordinator.port == "/dev/ttyUSB0"
    assert coordinator.baudrate == 38400


def test_coordinator_init_network():
    """Test d'initialisation réseau."""
    hass = MockHass()
    entry = MockEntry({
        "connection_type": const.CONNECTION_TYPE_NETWORK,
        "host": "192.168.1.100",
        "network_port": 10001,
    })
    
    coordinator = RFXCOMCoordinator(hass, entry)
    assert coordinator.connection_type == const.CONNECTION_TYPE_NETWORK
    assert coordinator.host == "192.168.1.100"
    assert coordinator.network_port == 10001


def test_build_arc_command_all_house_codes():
    """Test de tous les house codes."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    # Tester tous les house codes A-P
    for i, letter in enumerate("ABCDEFGHIJKLMNOP"):
        cmd = coordinator._build_arc_command(letter, "1", const.CMD_ON)
        assert cmd[4] == ord(letter), f"House code {letter} devrait être {ord(letter)}"


def test_build_arc_command_all_unit_codes():
    """Test de tous les unit codes."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    # Tester les unit codes 1-16
    for unit in range(1, 17):
        cmd = coordinator._build_arc_command("A", str(unit), const.CMD_ON)
        assert cmd[5] == unit, f"Unit code devrait être {unit}"


def test_build_arc_command_sequence_wraparound():
    """Test que le sequence number fait le tour."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    # Forcer le sequence number à 255
    coordinator._sequence_number = 255
    
    cmd = coordinator._build_arc_command("A", "1", const.CMD_ON)
    assert cmd[3] == 255
    
    # Le prochain devrait être 0
    cmd = coordinator._build_arc_command("A", "1", const.CMD_ON)
    assert cmd[3] == 0


def test_build_arc_command_invalid_house_code():
    """Test avec house code invalide."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    # House code invalide devrait utiliser le défaut (A = 0x41)
    cmd = coordinator._build_arc_command("", "1", const.CMD_ON)
    assert cmd[4] == 0x41  # Default to A
    
    cmd = coordinator._build_arc_command(None, "1", const.CMD_ON)
    assert cmd[4] == 0x41


def test_build_arc_command_invalid_unit_code():
    """Test avec unit code invalide."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    # Unit code invalide devrait utiliser 1 par défaut
    cmd = coordinator._build_arc_command("A", "", const.CMD_ON)
    assert cmd[5] == 1
    
    cmd = coordinator._build_arc_command("A", "invalid", const.CMD_ON)
    assert cmd[5] == 1


def test_hex_string_to_bytes_edge_cases():
    """Test des cas limites de conversion hex."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    # Chaîne vide
    result = coordinator._hex_string_to_bytes("", 4)
    assert len(result) == 4
    assert result == bytes([0x00, 0x00, 0x00, 0x00])
    
    # Chaîne trop longue
    result = coordinator._hex_string_to_bytes("0102030405060708090a0b0c0d0e0f10", 4)
    assert len(result) == 4
    assert result == bytes([0x01, 0x02, 0x03, 0x04])
    
    # Exactement la bonne longueur
    result = coordinator._hex_string_to_bytes("01020304", 4)
    assert len(result) == 4
    assert result == bytes([0x01, 0x02, 0x03, 0x04])


def test_build_ac_command():
    """Test de construction de commande AC."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    device_id = "0102030405060708"
    cmd = coordinator._build_ac_command(device_id, const.CMD_ON)
    
    assert len(cmd) == 12
    assert cmd[0] == 0x0B  # Longueur
    assert cmd[1] == 0x10  # Type AC
    assert cmd[2] == 0x00
    # Vérifier les bytes de l'ID
    assert cmd[3:11] == bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
    assert cmd[11] == 0x01  # ON
    
    # Test OFF
    cmd = coordinator._build_ac_command(device_id, const.CMD_OFF)
    assert cmd[11] == 0x00  # OFF


def test_build_ac_command_padding():
    """Test de padding pour AC avec ID court."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    # ID court devrait être complété avec des zéros
    cmd = coordinator._build_ac_command("01", const.CMD_ON)
    assert len(cmd) == 12
    assert cmd[3] == 0x01
    assert cmd[4:11] == bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


