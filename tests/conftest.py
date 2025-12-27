"""Configuration pytest."""
import pytest
from unittest.mock import Mock


@pytest.fixture(autouse=True)
def mock_hass():
    """Mock Home Assistant pour tous les tests."""
    with patch("homeassistant.core.HomeAssistant"):
        yield


