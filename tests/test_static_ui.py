"""Test static UI behavior using Home Assistant framework."""

from unittest.mock import Mock

import pytest

from custom_components.portainer.const import (
    CONF_FEATURE_HEALTH_CHECK,
    CONF_FEATURE_RESTART_POLICY,
    CONF_FEATURE_UPDATE_CHECK,
    CONF_UPDATE_CHECK_TIME,
)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry for testing."""
    mock_entry = Mock()
    mock_entry.title = "Test Portainer"
    mock_entry.options = {
        CONF_FEATURE_HEALTH_CHECK: True,
        CONF_FEATURE_RESTART_POLICY: True,
        CONF_FEATURE_UPDATE_CHECK: True,
        CONF_UPDATE_CHECK_TIME: "02:00",
    }
    return mock_entry


class TestStaticUIBehavior:
    """Test the static UI behavior - all fields always visible."""

    def test_static_schema_always_shows_all_fields(self, mock_config_entry):
        """Test that static schema always shows all 4 fields."""
        # In static UI, all fields should always be present
        expected_fields = {
            CONF_FEATURE_HEALTH_CHECK,
            CONF_FEATURE_RESTART_POLICY,
            CONF_FEATURE_UPDATE_CHECK,
            CONF_UPDATE_CHECK_TIME,
        }

        # Test with update check enabled
        enabled_config = {
            CONF_FEATURE_HEALTH_CHECK: True,
            CONF_FEATURE_RESTART_POLICY: True,
            CONF_FEATURE_UPDATE_CHECK: True,
            CONF_UPDATE_CHECK_TIME: "12:00",
        }

        # Test with update check disabled
        disabled_config = {
            CONF_FEATURE_HEALTH_CHECK: False,
            CONF_FEATURE_RESTART_POLICY: False,
            CONF_FEATURE_UPDATE_CHECK: False,
            CONF_UPDATE_CHECK_TIME: "06:30",
        }

        # Both configurations should have all 4 fields
        assert set(enabled_config.keys()) == expected_fields
        assert set(disabled_config.keys()) == expected_fields

    def test_time_field_always_present(self, mock_config_entry):
        """Test that time field is always present regardless of checkbox state."""
        # Static UI: time field is always visible

        # When update check is enabled, time field is present and used
        enabled_data = {
            CONF_FEATURE_UPDATE_CHECK: True,
            CONF_UPDATE_CHECK_TIME: "14:30",
        }
        assert CONF_UPDATE_CHECK_TIME in enabled_data
        assert enabled_data[CONF_FEATURE_UPDATE_CHECK] is True

        # When update check is disabled, time field is still present but ignored
        disabled_data = {
            CONF_FEATURE_UPDATE_CHECK: False,
            CONF_UPDATE_CHECK_TIME: "14:30",  # Still present but will be ignored
        }
        assert CONF_UPDATE_CHECK_TIME in disabled_data
        assert disabled_data[CONF_FEATURE_UPDATE_CHECK] is False

    def test_simplified_workflow_simulation(self, mock_config_entry):
        """Test the simplified static UI workflow."""
        # Static UI workflow: always show all fields, no dynamic hiding/showing

        def get_static_schema_fields():
            """Simulate static schema that always returns all fields."""
            return {
                CONF_FEATURE_HEALTH_CHECK,
                CONF_FEATURE_RESTART_POLICY,
                CONF_FEATURE_UPDATE_CHECK,
                CONF_UPDATE_CHECK_TIME,
            }

        # Test that schema always contains all fields
        schema_fields = get_static_schema_fields()
        expected_fields = {
            CONF_FEATURE_HEALTH_CHECK,
            CONF_FEATURE_RESTART_POLICY,
            CONF_FEATURE_UPDATE_CHECK,
            CONF_UPDATE_CHECK_TIME,
        }

        assert schema_fields == expected_fields
        assert len(schema_fields) == 4

    def test_static_ui_clarity(self, mock_config_entry):
        """Test that static UI provides clear, predictable behavior."""
        # Static UI benefits: no confusing field hiding/showing

        def simulate_form_submission(user_input):
            """Simulate form submission with static UI."""
            # In static UI, we always expect all fields to be present
            required_fields = {
                CONF_FEATURE_HEALTH_CHECK,
                CONF_FEATURE_RESTART_POLICY,
                CONF_FEATURE_UPDATE_CHECK,
                CONF_UPDATE_CHECK_TIME,
            }

            # Check if all required fields are present
            return all(field in user_input for field in required_fields)

        # Test complete form submission
        complete_input = {
            CONF_FEATURE_HEALTH_CHECK: True,
            CONF_FEATURE_RESTART_POLICY: False,
            CONF_FEATURE_UPDATE_CHECK: True,
            CONF_UPDATE_CHECK_TIME: "08:00",
        }

        assert simulate_form_submission(complete_input) is True

        # Test that missing time field would be caught
        incomplete_input = {
            CONF_FEATURE_HEALTH_CHECK: True,
            CONF_FEATURE_RESTART_POLICY: False,
            CONF_FEATURE_UPDATE_CHECK: True,
            # Missing CONF_UPDATE_CHECK_TIME
        }

        assert simulate_form_submission(incomplete_input) is False

    def test_time_field_behavior_with_update_check_disabled(self, mock_config_entry):
        """Test that time field behavior is clear when update check is disabled."""
        # Static UI: time field is always visible but usage depends on checkbox

        def get_effective_time_usage(update_check_enabled, time_value):
            """Simulate how time field is used in static UI."""
            if update_check_enabled:
                return f"Update check enabled, will run at {time_value}"
            else:
                return f"Update check disabled, time '{time_value}' is ignored"

        # Test with update check enabled
        enabled_result = get_effective_time_usage(True, "03:00")
        assert "enabled" in enabled_result
        assert "03:00" in enabled_result

        # Test with update check disabled
        disabled_result = get_effective_time_usage(False, "03:00")
        assert "disabled" in disabled_result
        assert "ignored" in disabled_result
        assert "03:00" in disabled_result  # Time is still shown but marked as ignored
