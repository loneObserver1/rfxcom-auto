"""Tests pour les entités sensor."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import sys

# Mock Home Assistant
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.components'] = MagicMock()
sys.modules['homeassistant.components.sensor'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()

# Mock CoordinatorEntity
class MockCoordinatorEntity:
    def __class_getitem__(cls, item):
        return MockCoordinatorEntity
    
    def __init__(self, coordinator):
        self.coordinator = coordinator

class MockSensorEntity:
    pass

sys.modules['homeassistant.helpers.update_coordinator'].CoordinatorEntity = MockCoordinatorEntity
sys.modules['homeassistant.components.sensor'].SensorEntity = MockSensorEntity

from custom_components.rfxcom.sensor import (
    RFXCOMTemperatureSensor,
    RFXCOMHumiditySensor,
    async_setup_entry,
)
from custom_components.rfxcom.const import (
    PROTOCOL_TEMP_HUM,
    CONF_PROTOCOL,
    CONF_DEVICE_ID,
)
from custom_components.rfxcom.coordinator import RFXCOMCoordinator


@pytest.fixture
def mock_coordinator():
    """Mock du coordinateur."""
    coordinator = Mock(spec=RFXCOMCoordinator)
    coordinator.get_discovered_devices = Mock(return_value={
        "26627": {
            CONF_PROTOCOL: PROTOCOL_TEMP_HUM,
            CONF_DEVICE_ID: "26627",
            "temperature": 21.2,
            "humidity": 39,
        }
    })
    return coordinator


@pytest.fixture
def mock_entry():
    """Mock d'une entrée de configuration."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.options = {
        "devices": [
            {
                "name": "Test Sensor",
                CONF_PROTOCOL: PROTOCOL_TEMP_HUM,
                CONF_DEVICE_ID: "26627",
            }
        ]
    }
    return entry


@pytest.fixture
def mock_hass(mock_coordinator):
    """Mock de Home Assistant."""
    hass = MagicMock()
    hass.data = {
        "rfxcom": {
            "test_entry": mock_coordinator
        }
    }
    return hass


class TestRFXCOMSensors:
    """Tests pour les capteurs RFXCOM."""

    def test_temperature_sensor_initialization(self, mock_coordinator):
        """Test d'initialisation du capteur de température."""
        sensor = RFXCOMTemperatureSensor(
            mock_coordinator,
            "Test Temperature",
            "26627",
            "test_temp"
        )
        
        assert sensor._attr_name == "Test Temperature"
        assert sensor._attr_unique_id == "test_temp"
        assert sensor._device_id == "26627"

    def test_humidity_sensor_initialization(self, mock_coordinator):
        """Test d'initialisation du capteur d'humidité."""
        sensor = RFXCOMHumiditySensor(
            mock_coordinator,
            "Test Humidity",
            "26627",
            "test_hum"
        )
        
        assert sensor._attr_name == "Test Humidity"
        assert sensor._attr_unique_id == "test_hum"
        assert sensor._device_id == "26627"

    def test_temperature_sensor_value(self, mock_coordinator):
        """Test de la valeur du capteur de température."""
        sensor = RFXCOMTemperatureSensor(
            mock_coordinator,
            "Test Temperature",
            "26627",
            "test_temp"
        )
        
        value = sensor.native_value
        
        assert value == 21.2

    def test_humidity_sensor_value(self, mock_coordinator):
        """Test de la valeur du capteur d'humidité."""
        sensor = RFXCOMHumiditySensor(
            mock_coordinator,
            "Test Humidity",
            "26627",
            "test_hum"
        )
        
        value = sensor.native_value
        
        assert value == 39

    def test_temperature_sensor_no_data(self, mock_coordinator):
        """Test du capteur de température sans données."""
        mock_coordinator.get_discovered_devices.return_value = {}
        
        sensor = RFXCOMTemperatureSensor(
            mock_coordinator,
            "Test Temperature",
            "26627",
            "test_temp"
        )
        
        value = sensor.native_value
        
        assert value is None

    def test_humidity_sensor_no_data(self, mock_coordinator):
        """Test du capteur d'humidité sans données."""
        mock_coordinator.get_discovered_devices.return_value = {}
        
        sensor = RFXCOMHumiditySensor(
            mock_coordinator,
            "Test Humidity",
            "26627",
            "test_hum"
        )
        
        value = sensor.native_value
        
        assert value is None

    @pytest.mark.asyncio
    async def test_setup_entry(self, mock_hass, mock_entry, mock_coordinator):
        """Test de configuration des capteurs."""
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, mock_entry, async_add_entities)
        
        # Vérifier que les entités ont été ajoutées (2 capteurs par appareil TEMP_HUM)
        assert async_add_entities.called
        call_args = async_add_entities.call_args[0][0]
        assert len(call_args) == 2  # Température + Humidité


