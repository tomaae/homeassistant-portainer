#!/usr/bin/env python3
"""Debug script to check entity creation."""

import sys
import os

# Add the custom_components path to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "custom_components"))


# Mock homeassistant modules to avoid import errors
class MockPlatform:
    SENSOR = "sensor"
    BUTTON = "button"


sys.modules["homeassistant"] = type(sys)("homeassistant")
sys.modules["homeassistant.const"] = type(sys)("homeassistant.const")
sys.modules["homeassistant.const"].Platform = MockPlatform
sys.modules["homeassistant.components"] = type(sys)("homeassistant.components")
sys.modules["homeassistant.components.sensor"] = type(sys)(
    "homeassistant.components.sensor"
)
sys.modules["homeassistant.components.sensor"].SensorEntityDescription = object
sys.modules["homeassistant.components.button"] = type(sys)(
    "homeassistant.components.button"
)
sys.modules["homeassistant.components.button"].ButtonEntity = object
sys.modules["homeassistant.helpers"] = type(sys)("homeassistant.helpers")
sys.modules["homeassistant.helpers.update_coordinator"] = type(sys)(
    "homeassistant.helpers.update_coordinator"
)
sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = object
sys.modules["homeassistant.helpers.entity_platform"] = type(sys)(
    "homeassistant.helpers.entity_platform"
)
sys.modules["homeassistant.helpers.entity_platform"].AddEntitiesCallback = object
sys.modules["homeassistant.config_entries"] = type(sys)("homeassistant.config_entries")
sys.modules["homeassistant.config_entries"].ConfigEntry = object
sys.modules["homeassistant.core"] = type(sys)("homeassistant.core")
sys.modules["homeassistant.core"].HomeAssistant = object

try:
    from portainer.sensor_types import SENSOR_TYPES
    from portainer.const import (
        PLATFORMS,
        CONF_FEATURE_UPDATE_CHECK,
        DEFAULT_FEATURE_UPDATE_CHECK,
    )

    print("=== PLATFORMS ===")
    for platform in PLATFORMS:
        print(f"  {platform}")

    print("\n=== SENSOR_TYPES ===")
    for sensor in SENSOR_TYPES:
        print(f"  Key: {sensor.key}")
        print(f"  Name: {sensor.name}")
        print(f"  ha_group: {sensor.ha_group}")
        print(f"  data_path: {sensor.data_path}")
        print(f"  data_attribute: {sensor.data_attribute}")
        print(f"  func: {sensor.func}")
        print(f"  data_reference: {sensor.data_reference}")
        print("  ---")

    print(f"\n=== FEATURE CONFIG ===")
    print(f"CONF_FEATURE_UPDATE_CHECK: {CONF_FEATURE_UPDATE_CHECK}")
    print(f"DEFAULT_FEATURE_UPDATE_CHECK: {DEFAULT_FEATURE_UPDATE_CHECK}")

    print("\n=== BUTTON PLATFORM CHECK ===")
    try:
        # Check if button file exists and is readable
        button_file = os.path.join(
            os.path.dirname(__file__), "custom_components", "portainer", "button.py"
        )
        print(f"Button file exists: {os.path.exists(button_file)}")
        if os.path.exists(button_file):
            with open(button_file, "r") as f:
                content = f.read()
                print(f"Button file size: {len(content)} characters")
                if "CONF_FEATURE_UPDATE_CHECK" in content:
                    print("Button file contains feature check")
                if "async_add_entities" in content:
                    print("Button file contains entity addition")

        from portainer.button import ForceUpdateCheckButton

        print("Button platform imports successfully")
        print(f"ForceUpdateCheckButton class exists: {ForceUpdateCheckButton}")
    except Exception as e:
        print(f"Button platform import error: {e}")
        import traceback

        traceback.print_exc()

    print("\n=== All imports successful ===")

except Exception as e:
    print(f"Import error: {e}")
    import traceback

    traceback.print_exc()
