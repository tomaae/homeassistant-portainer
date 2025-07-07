"""Config flow to configure Portainer."""

from __future__ import annotations

import re
from logging import getLogger
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
    CONF_SSL,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .api import PortainerAPI
from .const import (
    CONF_FEATURE_HEALTH_CHECK,  # feature switch
    CONF_FEATURE_RESTART_POLICY,
    CONF_FEATURE_UPDATE_CHECK,
    CONF_UPDATE_CHECK_TIME,
    DEFAULT_DEVICE_NAME,
    DEFAULT_FEATURE_HEALTH_CHECK,
    DEFAULT_FEATURE_RESTART_POLICY,
    DEFAULT_FEATURE_UPDATE_CHECK,
    DEFAULT_HOST,
    DEFAULT_SSL,
    DEFAULT_SSL_VERIFY,
    DEFAULT_UPDATE_CHECK_TIME,
    DOMAIN,
)

_LOGGER = getLogger(__name__)


def validate_time_string(value):
    """Validate time string in HH:MM format."""
    if not isinstance(value, str):
        raise vol.Invalid("Time must be a string in HH:MM format")
    
    # Check format with regex - allow single digit minutes too
    time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):([0-5]?[0-9])$')
    match = time_pattern.match(value)
    
    if not match:
        raise vol.Invalid("Time must be in HH:MM format (e.g., 04:30)")
    
    hours = int(match.group(1))
    minutes = int(match.group(2))
    
    # Additional validation (redundant but safe)
    if not (0 <= hours <= 23):
        raise vol.Invalid("Hours must be between 0 and 23")
    if not (0 <= minutes <= 59):
        raise vol.Invalid("Minutes must be between 0 and 59")
    
    return value


# ---------------------------
#   configured_instances
# ---------------------------
@callback
def configured_instances(hass):
    """Return a set of configured instances."""
    return {
        entry.data[CONF_NAME] for entry in hass.config_entries.async_entries(DOMAIN)
    }


# ---------------------------
#   PortainerConfigFlow
# ---------------------------
class PortainerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """PortainerConfigFlow class."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_import(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Occurs when a previous entry setup fails and is re-initiated."""
        return await self.async_step_user(user_input)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            # Check if instance with this name already exists
            if user_input[CONF_NAME] in configured_instances(self.hass):
                errors["base"] = "name_exists"
                # Return early if name already exists - no need to test connection
                return self._show_config_form(user_input=user_input, errors=errors)

            # Test connection only if name is unique
            api = await self.hass.async_add_executor_job(
                PortainerAPI,
                self.hass,
                user_input[CONF_HOST],
                user_input[CONF_API_KEY],
                user_input[CONF_SSL],
                user_input[CONF_VERIFY_SSL],
            )

            conn, errorcode = await self.hass.async_add_executor_job(
                api.connection_test
            )
            if not conn:
                errors[CONF_HOST] = errorcode
                _LOGGER.error("Portainer connection error (%s)", errorcode)

            # Save instance
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

            return self._show_config_form(user_input=user_input, errors=errors)

        return self._show_config_form(
            user_input={
                CONF_NAME: DEFAULT_DEVICE_NAME,
                CONF_HOST: DEFAULT_HOST,
                CONF_API_KEY: "",
                CONF_SSL: DEFAULT_SSL,
                CONF_VERIFY_SSL: DEFAULT_SSL_VERIFY,
            },
            errors=errors,
        )

    def _show_config_form(
        self, user_input: dict[str, Any] | None, errors: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the configuration form."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=user_input[CONF_NAME]): str,
                    vol.Required(CONF_HOST, default=user_input[CONF_HOST]): str,
                    vol.Required(CONF_API_KEY, default=user_input[CONF_API_KEY]): str,
                    vol.Optional(CONF_SSL, default=user_input[CONF_SSL]): bool,
                    vol.Optional(
                        CONF_VERIFY_SSL, default=user_input[CONF_VERIFY_SSL]
                    ): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PortainerOptionsFlow(config_entry)


class PortainerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for My Integration."""

    def __init__(self, config_entry):
        """Initialize the options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            # Check if this is a "toggle" request (update check status changed)
            current_update_check = self.config_entry.options.get(
                CONF_FEATURE_UPDATE_CHECK, DEFAULT_FEATURE_UPDATE_CHECK
            )
            new_update_check = user_input.get(CONF_FEATURE_UPDATE_CHECK, DEFAULT_FEATURE_UPDATE_CHECK)
            
            # If update check status changed, re-show form with updated schema
            if current_update_check != new_update_check:
                # Preserve current input values for the reload
                preserved_input = {
                    CONF_FEATURE_HEALTH_CHECK: user_input.get(
                        CONF_FEATURE_HEALTH_CHECK, 
                        self.config_entry.options.get(CONF_FEATURE_HEALTH_CHECK, DEFAULT_FEATURE_HEALTH_CHECK)
                    ),
                    CONF_FEATURE_RESTART_POLICY: user_input.get(
                        CONF_FEATURE_RESTART_POLICY,
                        self.config_entry.options.get(CONF_FEATURE_RESTART_POLICY, DEFAULT_FEATURE_RESTART_POLICY)
                    ),
                    CONF_FEATURE_UPDATE_CHECK: new_update_check,
                    CONF_UPDATE_CHECK_TIME: user_input.get(
                        CONF_UPDATE_CHECK_TIME,
                        self.config_entry.options.get(CONF_UPDATE_CHECK_TIME, DEFAULT_UPDATE_CHECK_TIME)
                    ),
                }
                
                # Generate schema with new update check status
                schema = self._get_dynamic_options_schema(new_update_check, preserved_input)
                
                return self.async_show_form(
                    step_id="init",
                    data_schema=schema,
                    description_placeholders=self._get_description_placeholders_with_temp(new_update_check)
                )
            
            # Validate time format if update check is enabled
            if user_input.get(CONF_FEATURE_UPDATE_CHECK, False):
                time_value = user_input.get(CONF_UPDATE_CHECK_TIME, DEFAULT_UPDATE_CHECK_TIME)
                if time_value:  # Only validate if time value is provided
                    try:
                        validate_time_string(time_value)
                    except vol.Invalid as e:
                        return self.async_show_form(
                            step_id="init",
                            data_schema=self._get_dynamic_options_schema(True, user_input),
                            errors={"base": str(e)},
                            description_placeholders=self._get_description_placeholders()
                        )
            
            # If update check was disabled, preserve current time for later use
            if not user_input.get(CONF_FEATURE_UPDATE_CHECK, False):
                user_input[CONF_UPDATE_CHECK_TIME] = self.config_entry.options.get(
                    CONF_UPDATE_CHECK_TIME, DEFAULT_UPDATE_CHECK_TIME
                )
            
            # Direct processing - no complex transformations needed
            return self.async_create_entry(title="", data=user_input)

        # Show options form
        current_update_check = self.config_entry.options.get(
            CONF_FEATURE_UPDATE_CHECK, DEFAULT_FEATURE_UPDATE_CHECK
        )
        schema = self._get_dynamic_options_schema(current_update_check)
        
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders=self._get_description_placeholders()
        )

    def _get_dynamic_options_schema(self, update_check_enabled, input_values=None):
        """Get the options schema with conditional time picker based on explicit status."""
        if input_values is None:
            input_values = {}
            
        # Base schema - always visible fields
        options_schema = {
            # Container Features
            vol.Optional(
                CONF_FEATURE_HEALTH_CHECK,
                default=input_values.get(
                    CONF_FEATURE_HEALTH_CHECK,
                    self.config_entry.options.get(CONF_FEATURE_HEALTH_CHECK, DEFAULT_FEATURE_HEALTH_CHECK)
                ),
                description="Enable health check monitoring for containers"
            ): bool,
            
            vol.Optional(
                CONF_FEATURE_RESTART_POLICY,
                default=input_values.get(
                    CONF_FEATURE_RESTART_POLICY,
                    self.config_entry.options.get(CONF_FEATURE_RESTART_POLICY, DEFAULT_FEATURE_RESTART_POLICY)
                ),
                description="Enable restart policy monitoring for containers"
            ): bool,
            
            # Update Check Feature
            vol.Optional(
                CONF_FEATURE_UPDATE_CHECK,
                default=update_check_enabled,
                description="Enable automatic container update checking"
            ): bool,
        }
        
        # Conditionally add time field ONLY if update check is enabled
        if update_check_enabled:
            options_schema[vol.Optional(
                CONF_UPDATE_CHECK_TIME,
                default=input_values.get(
                    CONF_UPDATE_CHECK_TIME,
                    self.config_entry.options.get(CONF_UPDATE_CHECK_TIME, DEFAULT_UPDATE_CHECK_TIME)
                ),
                description="Daily update check time in HH:MM format"
            )] = str
        
        return vol.Schema(options_schema)

    def _get_options_schema(self):
        """Get the options schema with conditional time picker."""
        # This method is kept for backwards compatibility but delegates to the dynamic version
        current_update_check = self.config_entry.options.get(
            CONF_FEATURE_UPDATE_CHECK, DEFAULT_FEATURE_UPDATE_CHECK
        )
        return self._get_dynamic_options_schema(current_update_check)

    def _get_description_placeholders(self):
        """Get description placeholders for the form."""
        current_update_check = self.config_entry.options.get(
            CONF_FEATURE_UPDATE_CHECK, DEFAULT_FEATURE_UPDATE_CHECK
        )
        current_time = self.config_entry.options.get(
            CONF_UPDATE_CHECK_TIME, DEFAULT_UPDATE_CHECK_TIME
        )
        
        if current_update_check:
            status_info = f"Update checking is currently enabled and runs daily at {current_time}"
        else:
            status_info = "Update checking is currently disabled"
        
        return {
            "update_status": "Enabled" if current_update_check else "Disabled",
            "current_time": current_time,
            "info": f"Configure Portainer monitoring features. {status_info}"
        }

    def _get_description_placeholders_with_temp(self, temp_update_check):
        """Get description placeholders with temporary update check status."""
        current_time = self.config_entry.options.get(
            CONF_UPDATE_CHECK_TIME, DEFAULT_UPDATE_CHECK_TIME
        )
        
        if temp_update_check:
            status_info = f"Update checking will be enabled. Set the time when checks should run daily."
        else:
            status_info = "Update checking will be disabled. Time setting is not needed."
        
        return {
            "update_status": "Will be Enabled" if temp_update_check else "Will be Disabled",
            "current_time": current_time,
            "info": f"Configure Portainer monitoring features. {status_info}"
        }
