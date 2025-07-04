"""Minimal Portainer config flow for debugging."""

from __future__ import annotations
from typing import Any
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult


class PortainerConfigFlow(ConfigFlow):
    """Minimal Portainer config flow for testing."""

    domain = "portainer"
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title="Portainer Test", 
                data={"host": "test"}
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host", default="localhost"): str,
            }),
        )
