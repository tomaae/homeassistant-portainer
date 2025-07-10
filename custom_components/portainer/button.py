"""Portainer button platform."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_FEATURE_UPDATE_CHECK, DEFAULT_FEATURE_UPDATE_CHECK, DOMAIN
from .coordinator import PortainerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(  # NOSONAR
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    # Always create the button - availability will be controlled dynamically
    button = ForceUpdateCheckButton(coordinator, config_entry.entry_id)
    async_add_entities([button])
    _LOGGER.debug("Force Update Check button created")


class ForceUpdateCheckButton(ButtonEntity):
    """Button to force immediate update check."""

    def __init__(self, coordinator: PortainerCoordinator, entry_id: str) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self.entry_id = entry_id

        # Set basic attributes
        self._attr_name = "Force Update Check"
        self._attr_icon = "mdi:update"
        self._attr_unique_id = f"{entry_id}_force_update_check_final"

        # Set default enabled state based on feature
        feature_enabled = coordinator.config_entry.options.get(
            CONF_FEATURE_UPDATE_CHECK, DEFAULT_FEATURE_UPDATE_CHECK
        )
        feature_enabled = feature_enabled is True
        self._attr_entity_registry_enabled_default = feature_enabled

        _LOGGER.debug(
            "Force Update Check button initialized: feature_enabled=%s, entity_enabled_default=%s",
            feature_enabled,
            self._attr_entity_registry_enabled_default,
        )

    @property
    def device_info(self):
        """Return device info to group with System device."""
        return {
            "identifiers": {
                (DOMAIN, f"{self.coordinator.name}_System_{self.entry_id}")
            },
            "name": f"{self.coordinator.name} System",
            "manufacturer": "Portainer",
        }

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        feature_enabled = self.coordinator.config_entry.options.get(
            CONF_FEATURE_UPDATE_CHECK, DEFAULT_FEATURE_UPDATE_CHECK
        )
        feature_enabled = feature_enabled is True
        coordinator_connected = self.coordinator.connected()

        _LOGGER.debug(
            "Button availability check: feature_enabled=%s, coordinator_connected=%s",
            feature_enabled,
            coordinator_connected,
        )

        return feature_enabled and coordinator_connected

    @property
    def entity_registry_enabled_default(self) -> bool:
        feature_enabled = self.coordinator.config_entry.options.get(
            CONF_FEATURE_UPDATE_CHECK, DEFAULT_FEATURE_UPDATE_CHECK
        )
        feature_enabled = feature_enabled is True
        _LOGGER.debug(
            "Button entity_registry_enabled_default called: %s", feature_enabled
        )
        return feature_enabled

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Force Update Check button pressed")
        await self.coordinator.force_update_check()

    async def async_update_entry(self, config_entry):
        """Handle config entry update (called after options change)."""
        self.coordinator.config_entry = config_entry
        self.async_write_ha_state()
