#!/usr/bin/env python3
"""Test if button platform is available."""

try:
    from homeassistant.components.button import ButtonEntity

    print("✓ ButtonEntity imported successfully")
    print(f"ButtonEntity module: {ButtonEntity.__module__}")
    print(f"ButtonEntity class: {ButtonEntity}")
except ImportError as e:
    print(f"✗ Failed to import ButtonEntity: {e}")

try:
    from homeassistant.const import Platform

    print(f"✓ Platform imported successfully")
    print(f"Platform.BUTTON: {Platform.BUTTON}")
except ImportError as e:
    print(f"✗ Failed to import Platform: {e}")
except AttributeError as e:
    print(f"✗ Platform.BUTTON not available: {e}")

# Test if we can create a minimal button class
try:

    class TestButton(ButtonEntity):
        def async_press(self):
            pass

    print("✓ Can create ButtonEntity subclass")
except Exception as e:
    print(f"✗ Cannot create ButtonEntity subclass: {e}")
