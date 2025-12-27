"""Tests pour l'auto-registry du coordinateur."""
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

# Mock Home Assistant
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

# Charger coordinator
coordinator_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'rfxcom', 'coordinator.py')
spec = importlib.util.spec_from_file_location("custom_components.rfxcom.coordinator", coordinator_path)
coordinator_module = importlib.util.module_from_spec(spec)
sys.modules['custom_components.rfxcom.coordinator'] = coordinator_module

with patch('serial.Serial'), patch('socket.socket'):
    spec.loader.exec_module(coordinator_module)

RFXCOMCoordinator = coordinator_module.RFXCOMCoordinator


class MockHass:
    def __init__(self):
        self.async_add_executor_job = AsyncMock()
        self.config_entries = MagicMock()
        self.config_entries.async_update_entry = AsyncMock()
        self.config_entries.async_reload = AsyncMock()


class MockEntry:
    def __init__(self, data, options=None):
        self.data = data
        self.options = options or {}
        self.entry_id = "test"
        self.async_update_entry = AsyncMock()


class TestAutoRegistry:
    """Tests pour l'auto-registry."""

    def test_get_discovered_devices(self):
        """Test de récupération des appareils découverts."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        devices = coordinator.get_discovered_devices()
        
        assert isinstance(devices, list)
        assert len(devices) == 0  # Initialement vide

    @pytest.mark.asyncio
    async def test_handle_discovered_device_arc(self):
        """Test de gestion d'un appareil ARC découvert."""
        hass = MockHass()
        entry = MockEntry(
            {"connection_type": const.CONNECTION_TYPE_USB},
            {const.CONF_AUTO_REGISTRY: True}
        )
        coordinator = RFXCOMCoordinator(hass, entry)
        
        device_info = {
            const.CONF_PROTOCOL: const.PROTOCOL_ARC,
            const.CONF_HOUSE_CODE: "A",
            const.CONF_UNIT_CODE: "1",
        }
        
        await coordinator._handle_discovered_device(device_info)
        
        # Vérifier que l'appareil a été ajouté aux découverts
        devices = coordinator.get_discovered_devices()
        assert len(devices) > 0

    @pytest.mark.asyncio
    async def test_handle_discovered_device_temp_hum(self):
        """Test de gestion d'un capteur TEMP_HUM découvert."""
        hass = MockHass()
        entry = MockEntry(
            {"connection_type": const.CONNECTION_TYPE_USB},
            {const.CONF_AUTO_REGISTRY: True}
        )
        coordinator = RFXCOMCoordinator(hass, entry)
        
        device_info = {
            const.CONF_PROTOCOL: const.PROTOCOL_TEMP_HUM,
            const.CONF_DEVICE_ID: "26627",
            "temperature": 21.2,
            "humidity": 39,
        }
        
        await coordinator._handle_discovered_device(device_info)
        
        devices = coordinator.get_discovered_devices()
        assert len(devices) > 0

    @pytest.mark.asyncio
    async def test_auto_register_device_arc(self):
        """Test d'auto-enregistrement d'un appareil ARC."""
        hass = MockHass()
        entry = MockEntry(
            {"connection_type": const.CONNECTION_TYPE_USB},
            {const.CONF_AUTO_REGISTRY: True}
        )
        coordinator = RFXCOMCoordinator(hass, entry)
        coordinator.entry = entry
        coordinator.hass = hass
        
        device_info = {
            const.CONF_PROTOCOL: const.PROTOCOL_ARC,
            const.CONF_HOUSE_CODE: "B",
            const.CONF_UNIT_CODE: "2",
        }
        
        unique_id = f"{device_info[const.CONF_PROTOCOL]}_{device_info.get(const.CONF_HOUSE_CODE, '')}_{device_info.get(const.CONF_UNIT_CODE, '')}"
        
        # S'assurer que entry.options est modifiable
        if "devices" not in entry.options:
            entry.options["devices"] = []
        
        await coordinator._auto_register_device(device_info, unique_id)
        
        # Vérifier que async_update_entry a été appelé
        assert hass.config_entries.async_update_entry.called
        call_args = hass.config_entries.async_update_entry.call_args
        assert call_args is not None
        updated_options = call_args[1].get("options", {})
        devices = updated_options.get("devices", [])
        assert len(devices) > 0
        assert devices[0][const.CONF_PROTOCOL] == const.PROTOCOL_ARC

    @pytest.mark.asyncio
    async def test_auto_register_device_temp_hum(self):
        """Test d'auto-enregistrement d'un capteur TEMP_HUM."""
        hass = MockHass()
        entry = MockEntry(
            {"connection_type": const.CONNECTION_TYPE_USB},
            {const.CONF_AUTO_REGISTRY: True}
        )
        coordinator = RFXCOMCoordinator(hass, entry)
        
        device_info = {
            const.CONF_PROTOCOL: const.PROTOCOL_TEMP_HUM,
            const.CONF_DEVICE_ID: "26627",
            "temperature": 21.2,
            "humidity": 39,
        }
        
        unique_id = f"{device_info[const.CONF_PROTOCOL]}_{device_info[const.CONF_DEVICE_ID]}"
        
        # S'assurer que entry.options est modifiable
        if "devices" not in entry.options:
            entry.options["devices"] = []
        
        await coordinator._auto_register_device(device_info, unique_id)
        
        # Vérifier que async_update_entry a été appelé
        assert hass.config_entries.async_update_entry.called
        call_args = hass.config_entries.async_update_entry.call_args
        assert call_args is not None
        updated_options = call_args[1].get("options", {})
        devices = updated_options.get("devices", [])
        assert len(devices) > 0
        assert devices[0][const.CONF_PROTOCOL] == const.PROTOCOL_TEMP_HUM
        assert "sensor_data" in devices[0]

    @pytest.mark.asyncio
    async def test_auto_register_device_already_exists(self):
        """Test d'auto-enregistrement d'un appareil déjà existant."""
        hass = MockHass()
        entry = MockEntry(
            {"connection_type": const.CONNECTION_TYPE_USB},
            {
                const.CONF_AUTO_REGISTRY: True,
                "devices": [
                    {
                        "name": "Existing Device",
                        const.CONF_PROTOCOL: const.PROTOCOL_ARC,
                        const.CONF_HOUSE_CODE: "A",
                        const.CONF_UNIT_CODE: "1",
                    }
                ]
            }
        )
        coordinator = RFXCOMCoordinator(hass, entry)
        coordinator.entry = entry
        
        device_info = {
            const.CONF_PROTOCOL: const.PROTOCOL_ARC,
            const.CONF_HOUSE_CODE: "A",
            const.CONF_UNIT_CODE: "1",
        }
        
        initial_count = len(entry.options.get("devices", []))
        unique_id = f"{device_info[const.CONF_PROTOCOL]}_{device_info.get(const.CONF_HOUSE_CODE, '')}_{device_info.get(const.CONF_UNIT_CODE, '')}"
        
        # Mock async_update_entry et async_reload
        entry.async_update_entry = AsyncMock()
        hass.config_entries.async_reload = AsyncMock()
        
        await coordinator._auto_register_device(device_info, unique_id)
        
        # L'appareil ne devrait pas être ajouté deux fois
        final_count = len(entry.options.get("devices", []))
        assert final_count == initial_count

