"""Constants used by the Portainer integration."""

from homeassistant.const import Platform
from typing import Final

PLATFORMS = [
    Platform.SENSOR,
]

DOMAIN = "portainer"
DEFAULT_NAME = "root"
ATTRIBUTION = "Data provided by Portainer integration"

SCAN_INTERVAL = 30

DEFAULT_HOST = "10.0.0.1"

DEFAULT_DEVICE_NAME = "Portainer"
DEFAULT_SSL = False
DEFAULT_SSL_VERIFY = True

# attributes used in the entity unique_id
DEVICE_ATTRIBUTES_CONTAINERS_UNIQUE = [
    "Environment",
    "Name",
    "ConfigEntryId",
]

TO_REDACT = {
    "password",
}

CUSTOM_ATTRIBUTE_ARRAY = "_Custom"

# fature switch
CONF_FEATURE_HEALTH_CHECK: Final = "feature_switch_health_check"
DEFAULT_FEATURE_HEALTH_CHECK = False
CONF_FEATURE_RESTART_POLICY: Final = "feature_switch_restart_policy"
DEFAULT_FEATURE_RESTART_POLICY = False
