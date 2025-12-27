"""Tests pour les constantes."""
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Importer directement const.py sans passer par __init__.py
import importlib.util
const_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'rfxcom', 'const.py')
spec = importlib.util.spec_from_file_location("const", const_path)
const = importlib.util.module_from_spec(spec)
spec.loader.exec_module(const)

DOMAIN = const.DOMAIN
DEFAULT_PORT = const.DEFAULT_PORT
DEFAULT_BAUDRATE = const.DEFAULT_BAUDRATE
DEFAULT_HOST = const.DEFAULT_HOST
DEFAULT_NETWORK_PORT = const.DEFAULT_NETWORK_PORT
CONNECTION_TYPE_USB = const.CONNECTION_TYPE_USB
CONNECTION_TYPE_NETWORK = const.CONNECTION_TYPE_NETWORK
PROTOCOL_AC = const.PROTOCOL_AC
PROTOCOL_ARC = const.PROTOCOL_ARC
CMD_ON = const.CMD_ON
CMD_OFF = const.CMD_OFF
PACKET_TYPE_LIGHTING1 = const.PACKET_TYPE_LIGHTING1
SUBTYPE_ARC = const.SUBTYPE_ARC


def test_constants():
    """Test que toutes les constantes sont définies."""
    assert DOMAIN == "rfxcom"
    assert DEFAULT_PORT == "/dev/ttyUSB0"
    assert DEFAULT_BAUDRATE == 38400
    assert DEFAULT_HOST == "localhost"
    assert DEFAULT_NETWORK_PORT == 10001
    assert CONNECTION_TYPE_USB == "usb"
    assert CONNECTION_TYPE_NETWORK == "network"
    assert PROTOCOL_AC == "AC"
    assert PROTOCOL_ARC == "ARC"
    assert CMD_ON == "ON"
    assert CMD_OFF == "OFF"
    assert PACKET_TYPE_LIGHTING1 == 0x10
    assert SUBTYPE_ARC == 0x01

