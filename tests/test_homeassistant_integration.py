"""
Integration tests using the official Home Assistant test framework.

This module tests the Portainer integration using the core Home Assistant interfaces
as recommended in the official documentation.
"""

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.portainer.const import (
    CONF_FEATURE_HEALTH_CHECK,
    CONF_FEATURE_RESTART_POLICY,
    CONF_FEATURE_UPDATE_CHECK,
    CONF_UPDATE_CHECK_TIME,
    DOMAIN,
)


class TestPortainerIntegrationHA:
    """Test Portainer integration with the Home Assistant test framework."""

    @pytest.mark.asyncio
    async def test_integration_setup_and_config_entry(self, hass: HomeAssistant):
        """Test setting up the integration via config entry."""
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

        # Add the config entry to Home Assistant
        config_entry.add_to_hass(hass)

        # Set up the integration via the core interface
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        # Assert the config entry state via the ConfigEntry.state attribute
        assert config_entry.state == ConfigEntryState.LOADED

        # Verify the integration is properly loaded
        assert DOMAIN in hass.config.components

    @pytest.mark.asyncio
    async def test_config_entry_options_update(self, hass: HomeAssistant):
        """Test updating config entry options via the core interface."""
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

        # Set up the integration
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        assert config_entry.state == ConfigEntryState.LOADED

        # Modify the config entry via the config entries interface
        new_options = {
            CONF_FEATURE_HEALTH_CHECK: True,
            CONF_FEATURE_RESTART_POLICY: True,
            CONF_FEATURE_UPDATE_CHECK: True,
            CONF_UPDATE_CHECK_TIME: "14:30",
        }

        # Update options via core interface
        hass.config_entries.async_update_entry(config_entry, options=new_options)
        await hass.async_block_till_done()

        # Assert the options were updated
        assert config_entry.options == new_options
        assert config_entry.options[CONF_FEATURE_UPDATE_CHECK] is True
        assert config_entry.options[CONF_UPDATE_CHECK_TIME] == "14:30"

    @pytest.mark.asyncio
    async def test_config_entry_unload_and_reload(self, hass: HomeAssistant):
        """Test unloading and reloading a config entry."""
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

        # Set up the integration
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        assert config_entry.state == ConfigEntryState.LOADED

        # Unload the config entry
        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

        assert config_entry.state == ConfigEntryState.NOT_LOADED

        # Reload the config entry
        await hass.config_entries.async_reload(config_entry.entry_id)
        await hass.async_block_till_done()

        assert config_entry.state == ConfigEntryState.LOADED

    @pytest.mark.asyncio
    async def test_integration_with_invalid_config(self, hass: HomeAssistant):
        """Test integration behavior with invalid configuration."""
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

        config_entry.add_to_hass(hass)

        # Try to set up the integration
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

        # The config entry should fail to load due to invalid config
        # This tests the integration's error handling
        assert config_entry.state in [
            ConfigEntryState.SETUP_ERROR,
            ConfigEntryState.SETUP_RETRY,
        ]
