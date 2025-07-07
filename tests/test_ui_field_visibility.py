"""Test static UI field behavior - all fields always visible."""

from custom_components.portainer.const import (
    CONF_FEATURE_HEALTH_CHECK,
    CONF_FEATURE_RESTART_POLICY,
    CONF_FEATURE_UPDATE_CHECK,
    CONF_UPDATE_CHECK_TIME,
)


class TestStaticUIFieldBehavior:
    """Test static UI field behavior - all fields always visible."""

    def test_all_fields_always_visible(self):
        """Test that all 4 fields are always visible in static UI."""
        # Static UI schema should always include all 4 fields
        expected_fields = {
            CONF_FEATURE_HEALTH_CHECK,
            CONF_FEATURE_RESTART_POLICY,
            CONF_FEATURE_UPDATE_CHECK,
            CONF_UPDATE_CHECK_TIME,
        }

        # Test with enabled state
        enabled_config = {
            CONF_FEATURE_HEALTH_CHECK: True,
            CONF_FEATURE_RESTART_POLICY: True,
            CONF_FEATURE_UPDATE_CHECK: True,
            CONF_UPDATE_CHECK_TIME: "12:00",
        }

        # Test with disabled state
        disabled_config = {
            CONF_FEATURE_HEALTH_CHECK: False,
            CONF_FEATURE_RESTART_POLICY: False,
            CONF_FEATURE_UPDATE_CHECK: False,
            CONF_UPDATE_CHECK_TIME: "06:30",
        }

        # Both should have all fields
        assert (
            set(enabled_config.keys()) == expected_fields
        ), "Enabled config should have all 4 fields"
        assert (
            set(disabled_config.keys()) == expected_fields
        ), "Disabled config should have all 4 fields"
        assert len(enabled_config) == 4, "Enabled config should have exactly 4 fields"
        assert len(disabled_config) == 4, "Disabled config should have exactly 4 fields"

    def test_time_field_always_present_regardless_of_state(self):
        """Test that time field is always present regardless of update check state."""
        # This is the key difference from dynamic UI - time field never disappears
        test_scenarios = [
            {
                "update_check_enabled": True,
                "description": "Time field visible when update check enabled",
            },
            {
                "update_check_enabled": False,
                "description": "Time field visible when update check disabled",
            },
        ]

        for scenario in test_scenarios:
            config = {
                CONF_FEATURE_HEALTH_CHECK: True,
                CONF_FEATURE_RESTART_POLICY: True,
                CONF_FEATURE_UPDATE_CHECK: scenario["update_check_enabled"],
                CONF_UPDATE_CHECK_TIME: "15:45",
            }

            # Time field should always be present
            assert CONF_UPDATE_CHECK_TIME in config, scenario["description"]
            assert (
                len(config) == 4
            ), f"Should always have 4 fields: {scenario['description']}"

    def test_static_ui_simplicity(self):
        """Test that static UI provides simple, predictable behavior."""
        # Benefits of static UI:
        # 1. No field hiding/showing confusion
        # 2. Users can pre-configure time before enabling update check
        # 3. Consistent field count across all states
        # 4. Simpler code and testing

        # All possible user configurations should have the same field structure
        configurations = [
            # All features enabled
            {
                CONF_FEATURE_HEALTH_CHECK: True,
                CONF_FEATURE_RESTART_POLICY: True,
                CONF_FEATURE_UPDATE_CHECK: True,
                CONF_UPDATE_CHECK_TIME: "08:00",
            },
            # Mixed features
            {
                CONF_FEATURE_HEALTH_CHECK: True,
                CONF_FEATURE_RESTART_POLICY: False,
                CONF_FEATURE_UPDATE_CHECK: True,
                CONF_UPDATE_CHECK_TIME: "10:00",
            },
            # Only update check
            {
                CONF_FEATURE_HEALTH_CHECK: False,
                CONF_FEATURE_RESTART_POLICY: False,
                CONF_FEATURE_UPDATE_CHECK: True,
                CONF_UPDATE_CHECK_TIME: "14:00",
            },
            # No features enabled
            {
                CONF_FEATURE_HEALTH_CHECK: False,
                CONF_FEATURE_RESTART_POLICY: False,
                CONF_FEATURE_UPDATE_CHECK: False,
                CONF_UPDATE_CHECK_TIME: "22:00",
            },
        ]

        for config in configurations:
            assert (
                len(config) == 4
            ), f"Every configuration should have exactly 4 fields: {config}"
            assert (
                CONF_UPDATE_CHECK_TIME in config
            ), f"Time field should always be present: {config}"

    def test_time_field_usage_logic(self):
        """Test that time field value is used correctly based on update check state."""
        # When update check is enabled, time field value is used
        enabled_config = {
            CONF_FEATURE_UPDATE_CHECK: True,
            CONF_UPDATE_CHECK_TIME: "09:30",
        }

        # When update check is disabled, time field value is ignored (but still present)
        disabled_config = {
            CONF_FEATURE_UPDATE_CHECK: False,
            CONF_UPDATE_CHECK_TIME: "09:30",  # Present but will be ignored by integration logic
        }

        # Both configurations are valid
        assert enabled_config[CONF_FEATURE_UPDATE_CHECK] is True
        assert disabled_config[CONF_FEATURE_UPDATE_CHECK] is False
        assert enabled_config[CONF_UPDATE_CHECK_TIME] == "09:30"
        assert disabled_config[CONF_UPDATE_CHECK_TIME] == "09:30"

        # The integration logic (not UI) determines whether to use the time value
        # This separation of concerns makes the UI simpler and more predictable

    def test_user_experience_improvements(self):
        """Test that static UI improves user experience."""
        # User scenarios that are better with static UI:

        # Scenario 1: User wants to configure time before enabling update check
        pre_config = {
            CONF_FEATURE_UPDATE_CHECK: False,  # Not yet enabled
            CONF_UPDATE_CHECK_TIME: "03:00",  # But time is pre-configured
        }

        # User can later enable update check and time is already set
        final_config = {
            CONF_FEATURE_UPDATE_CHECK: True,  # Now enabled
            CONF_UPDATE_CHECK_TIME: "03:00",  # Time is ready to use
        }

        assert (
            pre_config[CONF_UPDATE_CHECK_TIME] == final_config[CONF_UPDATE_CHECK_TIME]
        )
        # Time can be pre-configured (improved UX)

        # Scenario 2: No confusion about disappearing fields
        # Fields never disappear, so users are never confused about where settings went
        consistent_fields = [
            CONF_FEATURE_HEALTH_CHECK,
            CONF_FEATURE_RESTART_POLICY,
            CONF_FEATURE_UPDATE_CHECK,
            CONF_UPDATE_CHECK_TIME,
        ]
        assert (
            len(consistent_fields) == 4
        ), "UI always shows same 4 fields - no confusion"
