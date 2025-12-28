"""Tests basiques pour sensor.py avec mocks corrects."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock Home Assistant avant les imports
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.components'] = MagicMock()
sys.modules['homeassistant.components.sensor'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()
sys.modules['homeassistant.helpers.entity'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.helpers.device_registry'] = MagicMock()

# Mock CoordinatorEntity et SensorEntity
class MockCoordinatorEntity:
    def __class_getitem__(cls, item):
        return MockCoordinatorEntity
    
    def __init__(self, coordinator):
        self.coordinator = coordinator

class MockSensorEntity:
    pass

sys.modules['homeassistant.helpers.update_coordinator'].CoordinatorEntity = MockCoordinatorEntity
sys.modules['homeassistant.components.sensor'].SensorEntity = MockSensorEntity

# Mock DeviceInfo
class MockDeviceInfo:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

sys.modules['homeassistant.helpers.entity'].DeviceInfo = MockDeviceInfo

# Mock constants
sys.modules['homeassistant.const'].UnitOfTemperature = MagicMock()
sys.modules['homeassistant.const'].PERCENTAGE = "%"
sys.modules['homeassistant.const'].UnitOfTemperature.CELSIUS = "°C"

# Mock SensorDeviceClass et SensorStateClass
class MockSensorDeviceClass:
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"

class MockSensorStateClass:
    MEASUREMENT = "measurement"

sys.modules['homeassistant.components.sensor'].SensorDeviceClass = MockSensorDeviceClass
sys.modules['homeassistant.components.sensor'].SensorStateClass = MockSensorStateClass

from custom_components.rfxcom.sensor import RFXCOMTempHumSensor, async_setup_entry
from custom_components.rfxcom.const import PROTOCOL_TEMP_HUM, CONF_PROTOCOL, CONF_DEVICE_ID
from custom_components.rfxcom.coordinator import RFXCOMCoordinator


@pytest.fixture
def mock_coordinator():
    """Mock du coordinateur."""
    coordinator = Mock(spec=RFXCOMCoordinator)
    coordinator.get_discovered_devices = Mock(return_value=[
        {
            CONF_PROTOCOL: PROTOCOL_TEMP_HUM,
            CONF_DEVICE_ID: "26627",
            "temperature": 21.2,
            "humidity": 39,
            "status": "Dry",
        }
    ])
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
    
    # Mock device registry
    mock_dr = MagicMock()
    mock_device_entry = Mock()
    mock_dr.async_get.return_value = mock_dr
    mock_dr.async_get_or_create.return_value = mock_device_entry
    sys.modules['homeassistant.helpers.device_registry'].async_get = Mock(return_value=mock_dr)
    
    return hass


class TestRFXCOMTempHumSensor:
    """Tests pour RFXCOMTempHumSensor."""

    def test_sensor_initialization(self, mock_coordinator):
        """Test d'initialisation du capteur."""
        sensor = RFXCOMTempHumSensor(
            mock_coordinator,
            "Test Sensor",
            "26627",
            "test_sensor",
            device_info=MockDeviceInfo(identifiers={("rfxcom", "temp_hum_26627")}),
        )
        
        assert sensor._attr_name == "Test Sensor"
        assert sensor._attr_unique_id == "test_sensor"
        assert sensor._device_id == "26627"

    def test_sensor_temperature_value(self, mock_coordinator):
        """Test de la valeur de température."""
        sensor = RFXCOMTempHumSensor(
            mock_coordinator,
            "Test Sensor",
            "26627",
            "test_sensor",
        )
        
        value = sensor.native_value
        assert value == 21.2

    def test_sensor_extra_state_attributes(self, mock_coordinator):
        """Test des attributs supplémentaires."""
        sensor = RFXCOMTempHumSensor(
            mock_coordinator,
            "Test Sensor",
            "26627",
            "test_sensor",
        )
        
        # Forcer la mise à jour des valeurs
        _ = sensor.native_value
        
        attrs = sensor.extra_state_attributes
        assert attrs["humidity"] == 39
        assert attrs["status"] == "Dry"

    def test_sensor_no_data(self, mock_coordinator):
        """Test du capteur sans données."""
        mock_coordinator.get_discovered_devices.return_value = []
        
        sensor = RFXCOMTempHumSensor(
            mock_coordinator,
            "Test Sensor",
            "26627",
            "test_sensor",
        )
        
        value = sensor.native_value
        assert value is None
        
        attrs = sensor.extra_state_attributes
        assert attrs == {}

    @pytest.mark.asyncio
    async def test_setup_entry(self, mock_hass, mock_entry, mock_coordinator):
        """Test de configuration des capteurs."""
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, mock_entry, async_add_entities)
        
        # Vérifier qu'une seule entité a été ajoutée (composite)
        assert async_add_entities.called
        call_args = async_add_entities.call_args[0][0]
        assert len(call_args) == 1  # Une seule entité composite
        assert isinstance(call_args[0], RFXCOMTempHumSensor)

