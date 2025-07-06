"""Portainer sensor platform."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from logging import getLogger

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform as ep
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from custom_components.portainer.const import DOMAIN

from .coordinator import PortainerCoordinator
from .entity import PortainerEntity, async_create_sensors
from .sensor_types import SENSOR_SERVICES, SENSOR_TYPES  # noqa: F401

_LOGGER = getLogger(__name__)


# ---------------------------
#   async_setup_entry
# ---------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities_callback: AddEntitiesCallback,
):
    """Set up the sensor platform for a specific configuration entry."""
    # Set up entry for portainer component.
    dispatcher = {
        "PortainerSensor": PortainerSensor,
        "TimestampSensor": TimestampSensor,
        "UpdateCheckSensor": UpdateCheckSensor,
        "EndpointSensor": EndpointSensor,
        "ContainerSensor": ContainerSensor,
    }

    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    platform = ep.async_get_current_platform()

    services = platform.platform.SENSOR_SERVICES
    descriptions = platform.platform.SENSOR_TYPES

    for service in services:
        if service[0] not in hass.services.async_services().get(DOMAIN, {}):
            platform.async_register_entity_service(service[0], service[1], service[2])

    entities = await async_create_sensors(coordinator, descriptions, dispatcher)

    # Additional safety check: remove any duplicates by unique_id within the batch
    unique_entities = []
    seen_unique_ids = set()
    for entity in entities:
        if hasattr(entity, "unique_id") and entity.unique_id:
            if entity.unique_id not in seen_unique_ids:
                unique_entities.append(entity)
                seen_unique_ids.add(entity.unique_id)
            else:
                _LOGGER.warning(
                    "Removing duplicate entity with unique_id: %s", entity.unique_id
                )
        else:
            _LOGGER.warning("Entity without unique_id found during setup, skipping")

    async_add_entities_callback(unique_entities, update_before_add=True)

    @callback
    async def async_update_controller(coordinator):
        """Update entities when data changes."""
        from homeassistant.helpers import entity_registry as er

        # Use entity registry to get all existing entities for this config entry
        entity_registry = er.async_get(hass)
        existing_entities_in_registry = er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
        existing_unique_ids = {
            entity.unique_id
            for entity in existing_entities_in_registry
            if entity.unique_id and entity.platform == "portainer"
        }

        # Also check current platform entities as additional safety measure
        try:
            platform_entities = (
                platform._entities if hasattr(platform, "_entities") else []
            )
            platform_unique_ids = {
                entity.unique_id
                for entity in platform_entities
                if hasattr(entity, "unique_id") and entity.unique_id
            }
            existing_unique_ids.update(platform_unique_ids)
            _LOGGER.debug(
                "async_update_controller: registry=%d entities, platform=%d entities, total_unique_ids=%d",
                len(existing_entities_in_registry),
                len(platform_entities),
                len(existing_unique_ids),
            )
        except (AttributeError, TypeError) as e:
            _LOGGER.debug("Could not access platform entities: %s", e)

        new_entities = []
        entities = await async_create_sensors(coordinator, descriptions, dispatcher)
        for entity in entities:
            try:
                unique_id = entity.unique_id
                entity_name = entity.name
            except (AttributeError, TypeError, KeyError) as e:
                _LOGGER.error("Error accessing entity properties during update: %s", e)
                continue

            if not unique_id:
                _LOGGER.warning("Skipping entity with no unique_id during update")
                continue
            if not entity_name or entity_name.strip() == "":
                _LOGGER.warning(
                    "Skipping entity with no name during update: unique_id=%s",
                    unique_id,
                )
                continue
            if unique_id in existing_unique_ids:
                _LOGGER.debug("Skipping existing entity: %s", unique_id)
                continue

            _LOGGER.debug("Found new entity to add: %s", unique_id)
            new_entities.append(entity)
            # Add to existing set to prevent duplicates within this update cycle
            existing_unique_ids.add(unique_id)

        if new_entities:
            _LOGGER.info("Adding %d new entities", len(new_entities))
            async_add_entities_callback(new_entities, update_before_add=True)
        else:
            _LOGGER.debug("No new entities to add")

    # Connect listener per config_entry
    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{config_entry.entry_id}_update", async_update_controller
        )
    )


# ---------------------------
#   PortainerSensor
# ---------------------------
class PortainerSensor(PortainerEntity, SensorEntity):
    """Define an Portainer sensor."""

    def __init__(
        self,
        coordinator: PortainerCoordinator,
        description,
        uid: str | None = None,
    ):
        super().__init__(coordinator, description, uid)
        self._attr_suggested_unit_of_measurement = (
            self.description.suggested_unit_of_measurement
        )

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the value reported by the sensor."""
        return self._data[self.description.data_attribute]

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit the value is expressed in."""
        if self.description.native_unit_of_measurement:
            if self.description.native_unit_of_measurement.startswith("data__"):
                uom = self.description.native_unit_of_measurement[6:]
                if uom in self._data:
                    return self._data[uom]

            return self.description.native_unit_of_measurement


# ---------------------------
#   TimestampSensor
# ---------------------------
class TimestampSensor(PortainerSensor):
    """Sensor that handles timestamp values."""

    def __init__(
        self,
        coordinator: PortainerCoordinator,
        description,
        uid: str | None = None,
    ):
        super().__init__(coordinator, description, uid)
        self._attr_device_class = "timestamp"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # System sensors are always available, even if data isn't loaded yet
        return self.coordinator.connected()

    @property
    def native_value(self) -> datetime | str | None:
        """Return the timestamp value."""
        # Handle case where data might not be available yet
        if not hasattr(self, "_data") or not self._data:
            return "never"  # Return a valid status instead of "unavailable"

        value = self._data.get(self.description.data_attribute)
        if value and isinstance(value, str):
            if value in ["disabled", "never"]:
                return value  # Return the status as string
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return "never"  # Return valid status on error
        return "never"  # Default to valid status

    @property
    def device_class(self) -> str | None:
        """Return device class - only timestamp if we have a valid datetime."""
        # Handle case where data might not be available yet
        if not hasattr(self, "_data") or not self._data:
            return None

        value = self._data.get(self.description.data_attribute)
        if value and isinstance(value, str) and value not in ["disabled", "never"]:
            return "timestamp"
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        attrs = super().extra_state_attributes or {}

        # Handle case where data might not be available yet
        if not hasattr(self, "_data") or not self._data:
            return attrs

        value = self._data.get(self.description.data_attribute)
        if value in ["disabled", "never"]:
            attrs["status"] = value
        return attrs


# ---------------------------
#   EndpointsSensor
# ---------------------------
class EndpointSensor(PortainerSensor):
    """Define an Portainer sensor."""

    def __init__(
        self,
        coordinator: PortainerCoordinator,
        description,
        uid: str | None = None,
    ):
        super().__init__(coordinator, description, uid)
        self.manufacturer = "Portainer"


# ---------------------------
#   ContainerSensor
# ---------------------------
class ContainerSensor(PortainerSensor):
    """Define an Portainer sensor."""

    def __init__(
        self,
        coordinator: PortainerCoordinator,
        description,
        uid: str | None = None,
    ):
        super().__init__(coordinator, description, uid)
        self.sw_version = self.coordinator.data["endpoints"][self._data["EndpointId"]][
            "DockerVersion"
        ]
        if self.description.ha_group.startswith("data__"):
            dev_group = self.description.ha_group[6:]
            if (
                dev_group in self._data
                and self._data[dev_group] in self.coordinator.data["endpoints"]
            ):
                self.description.ha_group = self.coordinator.data["endpoints"][
                    self._data[dev_group]
                ]["Name"]


# ---------------------------
#   UpdateCheckSensor
# ---------------------------
class UpdateCheckSensor(PortainerSensor):
    """Single sensor for update check status across all containers."""

    def __init__(
        self,
        coordinator: PortainerCoordinator,
        description,
        uid: str | None = None,
    ):
        super().__init__(coordinator, description, uid)
        self._attr_icon = "mdi:clock-outline"
        self.manufacturer = "Portainer"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Always available if coordinator is connected, even if system data is missing
        return self.coordinator.connected()

    def _parse_datetime(self, value: str) -> datetime | str:
        """Parse ISO string to timezone-aware datetime object."""
        if isinstance(value, str) and value not in ["disabled", "never"]:
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                # Ensure timezone-aware datetime
                if dt.tzinfo is None:
                    try:
                        from zoneinfo import ZoneInfo

                        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                    except ImportError:
                        # Fallback for older Python versions
                        from datetime import timezone

                        dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                # If parsing fails, return as string
                return value
        return value

    def _get_time_until_text(self, target_datetime: datetime) -> str:
        """Get human-readable text for time until target datetime."""
        from datetime import timezone

        now = datetime.now(timezone.utc)
        if target_datetime.tzinfo is None:
            target_datetime = target_datetime.replace(tzinfo=timezone.utc)

        time_diff = target_datetime - now

        if time_diff.total_seconds() < 0:
            return "Overdue"

        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)

        if hours > 0:
            return f"in {hours} hour{'s' if hours != 1 else ''}"
        elif minutes > 0:
            return f"in {minutes} minute{'s' if minutes != 1 else ''}"
        else:
            return "in less than a minute"

    @property
    def native_value(self) -> str | datetime | None:
        """Return the update check status."""
        try:
            # Check if system data exists and has the required attribute
            if (
                "system" in self.coordinator.data
                and self.description.data_attribute in self.coordinator.data["system"]
            ):
                value = self.coordinator.data["system"][self.description.data_attribute]
            else:
                # Fallback: determine status manually
                update_enabled = self.coordinator.features.get(
                    "feature_switch_update_check", False
                )
                if not update_enabled:
                    return "disabled"

                next_update = self.coordinator.get_next_update_check_time()
                if next_update:
                    value = next_update.isoformat()
                else:
                    return "never"

            # Parse datetime for timestamp display
            parsed_value = self._parse_datetime(value)
            return parsed_value

        except (KeyError, AttributeError, TypeError):
            return "never"

    @property
    def name(self) -> str:
        """Return the name for this entity."""
        return "Container Update Check"

    @property
    def device_class(self) -> str | None:
        """Return device class - timestamp for datetime values."""
        value = self.native_value
        if isinstance(value, datetime):
            return "timestamp"
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        attrs = super().extra_state_attributes or {}

        # Add system update info from coordinator data
        try:
            # Current update feature status
            update_enabled = self.coordinator.features.get(
                "feature_switch_update_check", False
            )
            attrs["update_feature_enabled"] = update_enabled

            # Add user-friendly time display for datetime values
            value = self.native_value
            if isinstance(value, datetime):
                attrs["time_until_check"] = self._get_time_until_text(value)
                attrs["next_check_time"] = value.strftime("%Y-%m-%d %H:%M:%S %Z")
            elif value == "disabled":
                attrs["status_text"] = "Update check is disabled"
            elif value == "never":
                attrs["status_text"] = "Update check has never been scheduled"

            if "system" in self.coordinator.data:
                system_data = self.coordinator.data["system"]
                attrs["last_update_check"] = system_data.get(
                    "last_update_check", "never"
                )

            # Add container counts
            if "containers" in self.coordinator.data:
                attrs["total_containers"] = len(self.coordinator.data["containers"])

        except (KeyError, AttributeError, TypeError):
            pass

        return attrs
