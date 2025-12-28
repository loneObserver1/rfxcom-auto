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

# Créer un package mock pour les imports relatifs
sys.modules['custom_components'] = MagicMock()
sys.modules['custom_components.rfxcom'] = MagicMock()
sys.modules['custom_components.rfxcom.const'] = const

# Maintenant charger coordinator
coordinator_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'rfxcom', 'coordinator.py')
spec = importlib.util.spec_from_file_location("custom_components.rfxcom.coordinator", coordinator_path)
coordinator_module = importlib.util.module_from_spec(spec)
sys.modules['custom_components.rfxcom.coordinator'] = coordinator_module

# Mock les imports avant d'exécuter
with patch('serial.Serial'), patch('socket.socket'):
    spec.loader.exec_module(coordinator_module)

RFXCOMCoordinator = coordinator_module.RFXCOMCoordinator


class MockHass:
    def __init__(self):
        self.async_add_executor_job = AsyncMock()


class MockEntry:
    def __init__(self, data, options=None):
        self.data = data
        self.options = options or {}
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
        cmd = coordinator._build_lighting1_command(const.PROTOCOL_ARC, const.SUBTYPE_ARC, letter, "1", const.CMD_ON)
        assert cmd[4] == ord(letter), f"House code {letter} devrait être {ord(letter)}"


def test_build_arc_command_all_unit_codes():
    """Test de tous les unit codes."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    # Tester les unit codes 1-16
    for unit in range(1, 17):
        cmd = coordinator._build_lighting1_command(const.PROTOCOL_ARC, const.SUBTYPE_ARC, "A", str(unit), const.CMD_ON)
        assert cmd[5] == unit, f"Unit code devrait être {unit}"


def test_build_arc_command_sequence_wraparound():
    """Test que le sequence number fait le tour."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    # Forcer le sequence number à 254 (car il sera incrémenté à 255)
    coordinator._sequence_number = 254
    
    cmd = coordinator._build_lighting1_command(const.PROTOCOL_ARC, const.SUBTYPE_ARC, "A", "1", const.CMD_ON)
    assert cmd[3] == 255  # Incrémenté de 254 à 255
    
    # Le prochain devrait être 0 (255 + 1 = 256 % 256 = 0)
    cmd = coordinator._build_lighting1_command(const.PROTOCOL_ARC, const.SUBTYPE_ARC, "A", "1", const.CMD_ON)
    assert cmd[3] == 0


def test_build_arc_command_invalid_house_code():
    """Test avec house code invalide."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    # House code invalide devrait utiliser le défaut (A = 0x41)
    cmd = coordinator._build_lighting1_command(const.PROTOCOL_ARC, const.SUBTYPE_ARC, "", "1", const.CMD_ON)
    assert cmd[4] == 0x41  # Default to A
    
    cmd = coordinator._build_lighting1_command(const.PROTOCOL_ARC, const.SUBTYPE_ARC, None, "1", const.CMD_ON)
    assert cmd[4] == 0x41


def test_build_arc_command_invalid_unit_code():
    """Test avec unit code invalide."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    # Unit code invalide devrait utiliser 1 par défaut
    cmd = coordinator._build_lighting1_command(const.PROTOCOL_ARC, const.SUBTYPE_ARC, "A", "", const.CMD_ON)
    assert cmd[5] == 1
    
    cmd = coordinator._build_lighting1_command(const.PROTOCOL_ARC, const.SUBTYPE_ARC, "A", "invalid", const.CMD_ON)
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
    
    # Chaîne trop longue (tronquée en gardant les derniers bytes - LSB)
    result = coordinator._hex_string_to_bytes("0102030405060708090a0b0c0d0e0f10", 4)
    assert len(result) == 4
    # La fonction garde les 4 derniers bytes: 0x0d, 0x0e, 0x0f, 0x10
    assert result == bytes([0x0d, 0x0e, 0x0f, 0x10])
    
    # Exactement la bonne longueur
    result = coordinator._hex_string_to_bytes("01020304", 4)
    assert len(result) == 4
    assert result == bytes([0x01, 0x02, 0x03, 0x04])


def test_build_ac_command():
    """Test de construction de commande AC."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    device_id = "01020304"  # Lighting2 utilise 4 bytes, pas 8
    cmd = coordinator._build_lighting2_command(const.PROTOCOL_AC, const.SUBTYPE_AC, device_id, const.CMD_ON)
    
    assert len(cmd) == 12
    assert cmd[0] == 0x0B  # Longueur
    assert cmd[1] == 0x11  # Type Lighting2 (pas 0x10)
    assert cmd[2] == 0x00  # Subtype AC
    # Vérifier les bytes de l'ID (4 bytes)
    assert cmd[4:8] == bytes([0x01, 0x02, 0x03, 0x04])
    assert cmd[9] == 0x01  # ON command
    
    # Test OFF
    cmd = coordinator._build_lighting2_command(const.PROTOCOL_AC, const.SUBTYPE_AC, device_id, const.CMD_OFF)
    assert cmd[9] == 0x00  # OFF command


def test_build_ac_command_padding():
    """Test de padding pour AC avec ID court."""
    hass = MockHass()
    entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
    coordinator = RFXCOMCoordinator(hass, entry)
    
    # ID court devrait être complété avec des zéros au début (padding left, 4 bytes pour Lighting2)
    cmd = coordinator._build_lighting2_command(const.PROTOCOL_AC, const.SUBTYPE_AC, "01", const.CMD_ON)
    assert len(cmd) == 12
    # Avec padding left, "01" devient [0x00, 0x00, 0x00, 0x01]
    assert cmd[4:8] == bytes([0x00, 0x00, 0x00, 0x01])  # ID complété avec zéros au début


