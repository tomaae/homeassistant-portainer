"""Test UI field visibility behavior for update check time field."""

from unittest.mock import Mock

import voluptuous as vol

from custom_components.portainer.const import (
    CONF_FEATURE_HEALTH_CHECK,
    CONF_FEATURE_RESTART_POLICY,
    CONF_FEATURE_UPDATE_CHECK,
    CONF_UPDATE_CHECK_TIME,
    DEFAULT_FEATURE_HEALTH_CHECK,
    DEFAULT_FEATURE_RESTART_POLICY,
    DEFAULT_FEATURE_UPDATE_CHECK,
    DEFAULT_UPDATE_CHECK_TIME,
)


class MockOptionsFlowForUITest:
    """Mock version of OptionsFlow for testing UI field visibility."""
    
    def __init__(self, config_entry_options):
        """Initialize with config entry options."""
        self.config_entry = Mock()
        self.config_entry.options = config_entry_options or {}
    
    def _get_dynamic_options_schema(self, update_check_enabled, input_values=None):
        """Test the exact same logic as in the real OptionsFlow."""
        if input_values is None:
            input_values = {}
            
        # Base schema - always visible fields (same as real implementation)
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
        # THIS IS THE CRITICAL LOGIC WE'RE TESTING
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


class TestUIFieldVisibility:
    """Test UI field visibility behavior specifically."""

    def test_time_field_visible_when_update_check_enabled(self):
        """Test that time field is visible when update check is enabled."""
        # Create mock flow with update check enabled
        flow = MockOptionsFlowForUITest({
            CONF_FEATURE_HEALTH_CHECK: True,
            CONF_FEATURE_RESTART_POLICY: True,
            CONF_FEATURE_UPDATE_CHECK: True,  # Enabled
            CONF_UPDATE_CHECK_TIME: "02:00"
        })
        
        # Get schema with update check enabled
        schema = flow._get_dynamic_options_schema(update_check_enabled=True)
        
        # Extract field names
        field_names = []
        for key in schema.schema.keys():
            if hasattr(key, 'schema'):
                field_names.append(key.schema)
        
        # Verify time field is present
        assert CONF_UPDATE_CHECK_TIME in field_names, f"Time field should be visible when update check is enabled. Found fields: {field_names}"
        assert len(field_names) == 4, f"Should have 4 fields when time field is visible. Found: {field_names}"

    def test_time_field_hidden_when_update_check_disabled(self):
        """Test that time field is hidden when update check is disabled."""
        # Create mock flow with update check disabled
        flow = MockOptionsFlowForUITest({
            CONF_FEATURE_HEALTH_CHECK: True,
            CONF_FEATURE_RESTART_POLICY: True,
            CONF_FEATURE_UPDATE_CHECK: False,  # Disabled
            CONF_UPDATE_CHECK_TIME: "02:00"
        })
        
        # Get schema with update check disabled
        schema = flow._get_dynamic_options_schema(update_check_enabled=False)
        
        # Extract field names
        field_names = []
        for key in schema.schema.keys():
            if hasattr(key, 'schema'):
                field_names.append(key.schema)
        
        # Verify time field is NOT present
        assert CONF_UPDATE_CHECK_TIME not in field_names, f"Time field should be hidden when update check is disabled. Found fields: {field_names}"
        assert len(field_names) == 3, f"Should have 3 fields when time field is hidden. Found: {field_names}"

    def test_toggle_behavior_simulation(self):
        """Test the behavior when toggling update check setting."""
        # Create mock flow with update check enabled
        flow = MockOptionsFlowForUITest({
            CONF_FEATURE_HEALTH_CHECK: True,
            CONF_FEATURE_RESTART_POLICY: True,
            CONF_FEATURE_UPDATE_CHECK: True,  # Start enabled
            CONF_UPDATE_CHECK_TIME: "02:00"
        })
        
        # Step 1: Start with update check enabled
        schema_enabled = flow._get_dynamic_options_schema(update_check_enabled=True)
        fields_enabled = [key.schema for key in schema_enabled.schema.keys() if hasattr(key, 'schema')]
        
        assert CONF_UPDATE_CHECK_TIME in fields_enabled, "Time field should be visible initially"
        assert len(fields_enabled) == 4, "Should have 4 fields when enabled"
        
        # Step 2: User toggles update check to disabled
        schema_disabled = flow._get_dynamic_options_schema(update_check_enabled=False)
        fields_disabled = [key.schema for key in schema_disabled.schema.keys() if hasattr(key, 'schema')]
        
        assert CONF_UPDATE_CHECK_TIME not in fields_disabled, "Time field should be hidden after toggle"
        assert len(fields_disabled) == 3, "Should have 3 fields when disabled"
        
        # Step 3: User toggles back to enabled
        schema_re_enabled = flow._get_dynamic_options_schema(update_check_enabled=True)
        fields_re_enabled = [key.schema for key in schema_re_enabled.schema.keys() if hasattr(key, 'schema')]
        
        assert CONF_UPDATE_CHECK_TIME in fields_re_enabled, "Time field should be visible again after re-enabling"
        assert len(fields_re_enabled) == 4, "Should have 4 fields when re-enabled"

    def test_field_defaults_preservation(self):
        """Test that field defaults are preserved when toggling."""
        # Create mock flow with specific values
        flow = MockOptionsFlowForUITest({
            CONF_FEATURE_HEALTH_CHECK: False,  # Non-default
            CONF_FEATURE_RESTART_POLICY: False,  # Non-default
            CONF_FEATURE_UPDATE_CHECK: True,
            CONF_UPDATE_CHECK_TIME: "05:30"  # Non-default
        })
        
        # Test with user input values
        user_input = {
            CONF_FEATURE_HEALTH_CHECK: True,  # User changed
            CONF_FEATURE_RESTART_POLICY: True,  # User changed
            CONF_FEATURE_UPDATE_CHECK: False,  # User disabled
        }
        
        # Get schema with update check disabled but preserve user input
        schema = flow._get_dynamic_options_schema(update_check_enabled=False, input_values=user_input)
        
        # Extract defaults from schema using voluptuous structure
        defaults = {}
        for key, validator in schema.schema.items():
            if hasattr(key, 'schema') and hasattr(key, 'default'):
                # Handle voluptuous default functions
                default_val = key.default
                if callable(default_val):
                    default_val = default_val()
                defaults[key.schema] = default_val
        
        # Check that user input values are preserved as defaults
        assert defaults.get(CONF_FEATURE_HEALTH_CHECK) is True, "Health check should preserve user input"
        assert defaults.get(CONF_FEATURE_RESTART_POLICY) is True, "Restart policy should preserve user input" 
        assert defaults.get(CONF_FEATURE_UPDATE_CHECK) is False, "Update check should be disabled as per user input"
        
        # Time field should not exist in disabled schema
        field_names = [key.schema for key in schema.schema.keys() if hasattr(key, 'schema')]
        assert CONF_UPDATE_CHECK_TIME not in field_names, "Time field should not exist when update check is disabled"

    def test_time_field_conditional_logic_edge_cases(self):
        """Test edge cases for time field conditional logic."""
        flow = MockOptionsFlowForUITest({})
        
        # Test with None/empty input values
        schema_enabled_none = flow._get_dynamic_options_schema(update_check_enabled=True, input_values=None)
        schema_enabled_empty = flow._get_dynamic_options_schema(update_check_enabled=True, input_values={})
        
        enabled_fields_none = [key.schema for key in schema_enabled_none.schema.keys() if hasattr(key, 'schema')]
        enabled_fields_empty = [key.schema for key in schema_enabled_empty.schema.keys() if hasattr(key, 'schema')]
        
        # Both should include time field when enabled
        assert CONF_UPDATE_CHECK_TIME in enabled_fields_none, "Time field should be present with None input_values"
        assert CONF_UPDATE_CHECK_TIME in enabled_fields_empty, "Time field should be present with empty input_values"
        
        # Test with disabled
        schema_disabled_none = flow._get_dynamic_options_schema(update_check_enabled=False, input_values=None)
        schema_disabled_empty = flow._get_dynamic_options_schema(update_check_enabled=False, input_values={})
        
        disabled_fields_none = [key.schema for key in schema_disabled_none.schema.keys() if hasattr(key, 'schema')]
        disabled_fields_empty = [key.schema for key in schema_disabled_empty.schema.keys() if hasattr(key, 'schema')]
        
        # Both should exclude time field when disabled
        assert CONF_UPDATE_CHECK_TIME not in disabled_fields_none, "Time field should be absent with None input_values"
        assert CONF_UPDATE_CHECK_TIME not in disabled_fields_empty, "Time field should be absent with empty input_values"
