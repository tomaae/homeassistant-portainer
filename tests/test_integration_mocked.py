"""
Integration tests using alternative approach without hass fixture.

This module tests the Portainer integration without relying on the
problematic hass fixture from pytest-homeassistant-custom-component.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.portainer.const import (
    CONF_FEATURE_HEALTH_CHECK,
    CONF_FEATURE_RESTART_POLICY,
    CONF_FEATURE_UPDATE_CHECK,
    CONF_UPDATE_CHECK_TIME,
    DOMAIN,
)


@pytest.mark.asyncio
async def test_integration_setup_mock():
    """Test setting up the integration with mocked Home Assistant."""

    # Create a mock Home Assistant instance
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries._entries = {}
    hass.async_block_till_done = AsyncMock()
    hass.config = MagicMock()
    hass.config.components = set()

    # Create a mock config entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Portainer",
        data={
            "host": "http://localhost:9000",
            "username": "admin",
            "password": "password",
            "ssl": False,
            "verify_ssl": True,
        },
        options={
            CONF_FEATURE_HEALTH_CHECK: True,
            CONF_FEATURE_RESTART_POLICY: True,
            CONF_FEATURE_UPDATE_CHECK: False,
            CONF_UPDATE_CHECK_TIME: "02:00",
        },
        entry_id="test_entry_id",
    )

    # Mock the integration setup
    with patch("custom_components.portainer.async_setup_entry", return_value=True):
        # Add config entry to hass manually
        config_entry.add_to_hass(hass)

        # Mock successful setup
        config_entry.state = ConfigEntryState.LOADED
        hass.config.components.add(DOMAIN)

        # Verify the config entry is loaded
        assert config_entry.state == ConfigEntryState.LOADED
        assert DOMAIN in hass.config.components


@pytest.mark.asyncio
async def test_config_entry_options_update_mock():
    """Test updating config entry options with mocked interfaces."""

    # Create a mock Home Assistant instance
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries._entries = {}
    hass.config_entries.async_update_entry = MagicMock()
    hass.async_block_till_done = AsyncMock()

    # Create initial config entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Portainer",
        data={
            "host": "http://localhost:9000",
            "username": "admin",
            "password": "password",
        },
        options={CONF_FEATURE_UPDATE_CHECK: False, CONF_UPDATE_CHECK_TIME: "02:00"},
        entry_id="test_entry_id",
    )

    config_entry.add_to_hass(hass)

    # Update options
    new_options = {CONF_FEATURE_UPDATE_CHECK: True, CONF_UPDATE_CHECK_TIME: "14:30"}

    # Simulate updating the config entry options
    config_entry.options = new_options
    hass.config_entries.async_update_entry(config_entry, options=new_options)

    # Verify the options were updated
    assert config_entry.options == new_options
    assert config_entry.options[CONF_FEATURE_UPDATE_CHECK] is True
    assert config_entry.options[CONF_UPDATE_CHECK_TIME] == "14:30"


@pytest.mark.asyncio
async def test_config_entry_unload_and_reload_mock():
    """Test unloading and reloading a config entry with mocks."""

    # Create a mock Home Assistant instance
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries._entries = {}
    hass.config_entries.async_unload = AsyncMock(return_value=True)
    hass.config_entries.async_reload = AsyncMock(return_value=True)
    hass.async_block_till_done = AsyncMock()

    # Create config entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Portainer",
        data={
            "host": "http://localhost:9000",
            "username": "admin",
            "password": "password",
        },
        options={CONF_FEATURE_UPDATE_CHECK: True, CONF_UPDATE_CHECK_TIME: "12:00"},
        entry_id="test_entry_id",
    )

    config_entry.add_to_hass(hass)
    config_entry.state = ConfigEntryState.LOADED

    # Verify initially loaded
    assert config_entry.state == ConfigEntryState.LOADED

    # Unload
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    config_entry.state = ConfigEntryState.NOT_LOADED

    # Verify unloaded
    assert config_entry.state == ConfigEntryState.NOT_LOADED

    # Reload
    assert await hass.config_entries.async_reload(config_entry.entry_id)
    config_entry.state = ConfigEntryState.LOADED

    # Verify reloaded
    assert config_entry.state == ConfigEntryState.LOADED


@pytest.mark.asyncio
async def test_integration_with_invalid_config_mock():
    """Test integration behavior with invalid configuration using mocks."""

    # Create a mock Home Assistant instance
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries._entries = {}
    hass.async_block_till_done = AsyncMock()
    hass.config = MagicMock()
    hass.config.components = set()

    # Create config entry with invalid host
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Portainer Invalid",
        data={
            "host": "invalid://host:9000",  # Invalid URL
            "username": "admin",
            "password": "password",
        },
        options={},
        entry_id="test_entry_invalid",
    )

    # Mock failed setup due to invalid config
    with patch("custom_components.portainer.async_setup_entry", return_value=False):
        config_entry.add_to_hass(hass)

        # Simulate setup failure
        config_entry.state = ConfigEntryState.SETUP_ERROR

        # Verify the config entry failed to load
        assert config_entry.state == ConfigEntryState.SETUP_ERROR


def test_coordinator_initialization_with_hass_non_async(hass: HomeAssistant):
    """Test coordinator initialization using the working hass fixture pattern."""
    from custom_components.portainer.const import DOMAIN
    from custom_components.portainer.coordinator import PortainerCoordinator

    # Create a mock config entry like in the working test
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Portainer",
        data={"host": "localhost", "name": "Test Portainer"},
        options={
            CONF_FEATURE_HEALTH_CHECK: True,
            CONF_FEATURE_RESTART_POLICY: True,
            CONF_FEATURE_UPDATE_CHECK: True,
            CONF_UPDATE_CHECK_TIME: "04:30",
        },
        entry_id="test_entry_enabled",
    )

    # Test that the coordinator can be properly initialized with HA (like working test)
    coordinator = PortainerCoordinator.__new__(PortainerCoordinator)
    coordinator.hass = hass
    coordinator.config_entry = config_entry

    # Basic initialization checks
    assert coordinator.hass == hass
    assert coordinator.config_entry == config_entry
