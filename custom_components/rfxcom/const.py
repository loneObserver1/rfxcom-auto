"""Constantes pour l'intégration RFXCOM."""

DOMAIN = "rfxcom"
DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUDRATE = 38400
DEFAULT_HOST = "localhost"
DEFAULT_NETWORK_PORT = 10001

# Types de connexion
CONNECTION_TYPE_USB = "usb"
CONNECTION_TYPE_NETWORK = "network"

# Protocoles supportés
PROTOCOL_AC = "AC"
PROTOCOL_ARC = "ARC"
PROTOCOL_TEMP_HUM = "TEMP_HUM"

# Types d'appareils
DEVICE_TYPE_SWITCH = "switch"
DEVICE_TYPE_LIGHT = "light"
DEVICE_TYPE_SENSOR = "sensor"

# Commandes
CMD_ON = "ON"
CMD_OFF = "OFF"

# Configuration
CONF_PORT = "port"
CONF_BAUDRATE = "baudrate"
CONF_HOST = "host"
CONF_NETWORK_PORT = "network_port"
CONF_CONNECTION_TYPE = "connection_type"
CONF_PROTOCOL = "protocol"
CONF_UNIT_CODE = "unit_code"
CONF_HOUSE_CODE = "house_code"
CONF_DEVICE_ID = "device_id"
CONF_PAIRING_MODE = "pairing_mode"

# RFXCOM Packet Types
PACKET_TYPE_LIGHTING1 = 0x10
PACKET_TYPE_AC = 0x10
PACKET_TYPE_TEMP_HUM = 0x52
SUBTYPE_ARC = 0x01
SUBTYPE_TH13 = 0x0D  # Alecto WS1700 and compatibles

# Auto-registry
CONF_AUTO_REGISTRY = "auto_registry"
DEFAULT_AUTO_REGISTRY = False

# Timeouts
PAIRING_TIMEOUT = 30  # secondes

