"""
EntityFactory: Encapsulates Portainer entity creation, validation, and filtering workflow.
This class centralizes all logic for instantiating, validating, and filtering entities,
making the process explicit, maintainable, and easy to extend for new entity types.
"""

from logging import getLogger

_LOGGER = getLogger(__name__)


class EntityFactory:
    def __init__(self, coordinator, dispatcher):
        self.coordinator = coordinator
        self.dispatcher = dispatcher

    def create_sensors(self, descriptions):
        """Create Portainer sensor entities."""
        new_entities = []
        for description in descriptions:
            if description.data_path not in self.coordinator.data:
                self.coordinator.data[description.data_path] = {}
            data = self.coordinator.data[description.data_path]
            if not description.data_reference:
                self._process_description_without_reference(
                    new_entities, description, data
                )
            else:
                self._process_description_with_reference(
                    new_entities, description, data
                )
        final_entities = [
            entity for entity in new_entities if self._final_entity_validation(entity)
        ]
        _LOGGER.debug("Returning %d validated entities", len(final_entities))
        return final_entities

    def _should_create_entity(self, description, data):
        if description.func == "UpdateCheckSensor":
            return True
        if (
            data.get(description.data_attribute) is None
            and description.func != "TimestampSensor"
        ):
            return False
        return True

    def _create_temp_entity(self, func, description, uid=None):
        if uid is not None:
            return self.dispatcher[func](self.coordinator, description, uid)
        return self.dispatcher[func](self.coordinator, description)

    def _validate_entity(self, temp_obj, description, uid=None):
        try:
            unique_id = temp_obj.unique_id
            entity_name = temp_obj.name
        except (AttributeError, TypeError, KeyError) as e:
            if uid is not None:
                _LOGGER.error(
                    "Error accessing properties of entity %s (uid: %s): %s",
                    description.key,
                    uid,
                    e,
                )
            else:
                _LOGGER.error(
                    "Error accessing properties of entity %s: %s", description.key, e
                )
            return None, None
        return unique_id, entity_name

    def _is_valid_entity(self, unique_id, entity_name, description, uid=None):
        if not unique_id or unique_id.strip() == "":
            if uid is not None:
                _LOGGER.warning(
                    "Skipping entity creation for %s (uid: %s): unique_id is None or empty (%s)",
                    description.key,
                    uid,
                    repr(unique_id),
                )
            else:
                _LOGGER.warning(
                    "Skipping entity creation for %s: unique_id is None or empty (%s)",
                    description.key,
                    repr(unique_id),
                )
            return False
        if not entity_name or entity_name.strip() == "":
            if uid is not None:
                _LOGGER.warning(
                    "Skipping entity creation for %s (uid: %s): name is None or empty (%s)",
                    description.key,
                    uid,
                    repr(entity_name),
                )
            else:
                _LOGGER.warning(
                    "Skipping entity creation for %s: name is None or empty (%s)",
                    description.key,
                    repr(entity_name),
                )
            return False
        return True

    def _final_entity_validation(self, entity):
        try:
            unique_id = entity.unique_id
            entity_name = entity.name
            entity_id = getattr(entity, "entity_id", None)
            if not unique_id or unique_id.strip() == "":
                _LOGGER.error(
                    "Filtering out entity with invalid unique_id: %s (name: %s, entity_id: %s)",
                    repr(unique_id),
                    repr(entity_name),
                    repr(entity_id),
                )
                return False
            if not entity_name or entity_name.strip() == "":
                _LOGGER.error(
                    "Filtering out entity with invalid name: %s (unique_id: %s, entity_id: %s)",
                    repr(entity_name),
                    repr(unique_id),
                    repr(entity_id),
                )
                return False
            _LOGGER.debug(
                "Final entity validation passed: unique_id=%s, name=%s, entity_id=%s",
                unique_id,
                entity_name,
                entity_id,
            )
            return True
        except (AttributeError, TypeError, KeyError) as e:
            _LOGGER.error("Error validating entity during final check: %s", e)
            return False

    def _add_entity_if_valid(self, new_entities, temp_obj, description, uid=None):
        unique_id, entity_name = self._validate_entity(temp_obj, description, uid)
        if not self._is_valid_entity(unique_id, entity_name, description, uid):
            return
        if any(e.unique_id == unique_id for e in new_entities):
            _LOGGER.debug(
                "Entity with unique_id %s already in new_entities, skipping", unique_id
            )
            return
        if uid is not None:
            _LOGGER.debug(
                "Adding entity with uid to new_entities: unique_id=%s, name=%s, uid=%s, type=%s",
                unique_id,
                entity_name,
                uid,
                type(temp_obj).__name__,
            )
        else:
            _LOGGER.debug(
                "Adding entity to new_entities: unique_id=%s, name=%s, type=%s",
                unique_id,
                entity_name,
                type(temp_obj).__name__,
            )
        new_entities.append(temp_obj)

    def _process_description_without_reference(self, new_entities, description, data):
        if not self._should_create_entity(description, data):
            return
        temp_obj = self._create_temp_entity(description.func, description)
        self._add_entity_if_valid(new_entities, temp_obj, description)

    def _process_description_with_reference(self, new_entities, description, data):
        for uid in data:
            temp_obj = self._create_temp_entity(description.func, description, uid)
            self._add_entity_if_valid(new_entities, temp_obj, description, uid)
