"""Configuration pytest avec mocks Home Assistant."""
import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
from typing import Any

# Mock Home Assistant avant les imports
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.exceptions'] = MagicMock()
sys.modules['homeassistant.data_entry_flow'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()
sys.modules['homeassistant.helpers.restore_state'] = MagicMock()
sys.modules['homeassistant.components.switch'] = MagicMock()

# Mock des constantes Home Assistant
from homeassistant.const import Platform
from homeassistant.data_entry_flow import FlowResultType

# Créer les mocks nécessaires
mock_platform = Mock()
mock_platform.SWITCH = "switch"
Platform.SWITCH = "switch"

mock_flow_result = Mock()
FlowResultType.FORM = "form"
FlowResultType.CREATE_ENTRY = "create_entry"
FlowResultType.MENU = "menu"

@pytest.fixture(autouse=True)
def mock_hass_components():
    """Mock automatique des composants Home Assistant."""
    with patch('homeassistant.config_entries.ConfigEntry'), \
         patch('homeassistant.core.HomeAssistant'), \
         patch('homeassistant.helpers.update_coordinator.DataUpdateCoordinator'), \
         patch('homeassistant.components.switch.SwitchEntity'), \
         patch('homeassistant.helpers.restore_state.RestoreEntity'):
        yield
