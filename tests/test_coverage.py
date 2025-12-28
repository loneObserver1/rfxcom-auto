"""Tests pour améliorer la couverture de code."""
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Importer const directement
import importlib.util
const_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'rfxcom', 'const.py')
spec = importlib.util.spec_from_file_location("rfxcom.const", const_path)
const_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(const_module)

# Maintenant on peut tester
def test_const_module_imported():
    """Test que le module const peut être importé."""
    assert const_module.DOMAIN == "rfxcom"
    assert const_module.DEFAULT_PORT == "/dev/ttyUSB0"
    assert const_module.PROTOCOL_ARC == "ARC"
    assert const_module.PROTOCOL_AC == "AC"
    assert const_module.CMD_ON == "ON"
    assert const_module.CMD_OFF == "OFF"
    assert const_module.PACKET_TYPE_LIGHTING1 == 0x10
    assert const_module.SUBTYPE_ARC == 0x01


def test_all_constants_defined():
    """Test que toutes les constantes importantes sont définies."""
    required_constants = [
        'DOMAIN', 'DEFAULT_PORT', 'DEFAULT_BAUDRATE', 'DEFAULT_HOST',
        'DEFAULT_NETWORK_PORT', 'CONNECTION_TYPE_USB', 'CONNECTION_TYPE_NETWORK',
        'PROTOCOL_AC', 'PROTOCOL_ARC', 'CMD_ON', 'CMD_OFF',
        'PACKET_TYPE_LIGHTING1', 'SUBTYPE_ARC',
        'CONF_PORT', 'CONF_BAUDRATE', 'CONF_HOST', 'CONF_NETWORK_PORT',
        'CONF_CONNECTION_TYPE', 'CONF_PROTOCOL', 'CONF_UNIT_CODE',
        'CONF_HOUSE_CODE', 'CONF_DEVICE_ID',
    ]
    
    for const_name in required_constants:
        assert hasattr(const_module, const_name), f"Constante {const_name} manquante"
        value = getattr(const_module, const_name)
        assert value is not None, f"Constante {const_name} est None"


