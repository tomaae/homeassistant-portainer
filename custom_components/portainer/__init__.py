"""The Portainer integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import PortainerCoordinator

_LOGGER = logging.getLogger(__name__)


# ---------------------------
#   update_listener
# ---------------------------
async def _async_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


# ---------------------------
#   async_setup_entry
# ---------------------------
async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    if DOMAIN not in hass.data or config_entry.entry_id not in hass.data[DOMAIN]:
        hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = {
            "coordinator": None,
            "entities": {},
        }

    coordinator = PortainerCoordinator(hass, config_entry)
    hass.data[DOMAIN][config_entry.entry_id]["coordinator"] = coordinator
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    config_entry.async_on_unload(
        config_entry.add_update_listener(_async_update_listener)
    )

    return True


# ---------------------------
#   async_unload_entry
# ---------------------------
async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""

    # Retrieve stored data for this config_entry
    entry_data = hass.data[DOMAIN].pop(config_entry.entry_id, None)

    if not entry_data:
        return False  # Nothing to unload

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    return unload_ok
