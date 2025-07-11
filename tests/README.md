# Portainer Integration - Unit Tests Documentation

## Overview

This directory contains comprehensive unit tests for the Portainer Home Assistant integration, covering all major functionality including config flows, entity management, update checks, and UI behavior. All tests follow Home Assistant testing best practices and are fully compatible with VS Code test discovery.

## Current Test Files (110 Tests Total)

### 1. `test_pure_logic.py` ✅ (24 tests)

- **Purpose**: Tests core config flow logic without Home Assistant framework dependencies
- **Coverage**: Dynamic UI behavior, time validation, schema generation, error handling
- **Features**: Pure Python tests, most reliable for CI/CD pipelines

### 2. `test_availability_fix.py` ✅ (12 tests)

- **Purpose**: Tests entity availability logic for buttons and sensors
- **Coverage**: Feature toggle behavior, default states, option handling
- **Features**: Ensures entities are properly enabled/disabled based on feature flags

### 3. `test_dynamic_ui_reactive.py` ✅ (4 tests)

- **Purpose**: Tests dynamic UI behavior and reactive form updates
- **Coverage**: Checkbox detection, schema generation, description updates
- **Features**: Validates responsive UI changes based on user input

### 4. `test_tag_parsing.py` ✅ (37 tests)

- **Purpose**: Tests Docker image name and tag parsing functionality
- **Coverage**: Complex registry URLs, digest handling, image ID normalization
- **Features**: Comprehensive parsing of various Docker image formats

### 5. `test_ui_field_visibility.py` ✅ (5 tests)

- **Purpose**: Tests conditional field visibility in config flows
- **Coverage**: Time field display logic, toggle behavior, edge cases
- **Features**: Ensures UI fields appear/disappear correctly

### 6. `test_unique_id_fix.py` ✅ (8 tests)

- **Purpose**: Tests unique ID generation for entities
- **Coverage**: Endpoint ID handling, collision avoidance, error scenarios
- **Features**: Prevents duplicate entity registration issues

### 7. `test_update_checks.py` ✅ (20 tests)

- **Purpose**: Tests container update check functionality
- **Coverage**: Update scheduling, API responses, cache management
- **Features**: Validates update detection and timing logic

## Key Features Tested

✅ **Entity Availability Management**

- Proper entity enabled/disabled states based on feature configurations
- Backward compatibility with existing installations
- Default behavior for new integrations

✅ **Dynamic UI Behavior**

- Time field only appears when "Container Update Check" is enabled
- Form reloads properly when toggling checkboxes
- Field count consistency and reactive updates

✅ **Docker Image Processing**

- Complex registry URL parsing (including ports, namespaces)
- Digest removal and tag normalization
- Image ID handling and validation

✅ **Update Check Logic**

- Proper scheduling based on configured times
- API response handling (dict/list formats)
- Cache management and invalidation

✅ **Unique ID Generation**

- Collision avoidance for entity registration
- Proper handling of missing endpoint data
- Multi-config-entry scenarios

✅ **Time Validation**

- Accepts HH:MM format including single digits (e.g., "9:5")
- Rejects invalid formats, hours >23, minutes >59
- Proper error messages for different invalid inputs

✅ **Schema Generation**

- Correct field types (bool for features, str for time)
- Proper default value handling from config entry
- Input value preservation across form state changes

✅ **Error Handling**

- Graceful handling of None/empty config entries
- Invalid input type handling
- Missing configuration field handling

## Running Tests

### Quick Test (All Tests)

```bash
cd /home/hass/homeassistant-portainer
python -m pytest tests/ -v
```

### Individual Test Files

```bash
# Core logic tests (recommended for development)
python -m pytest tests/test_pure_logic.py -v

# Entity availability tests
python -m pytest tests/test_availability_fix.py -v

# Docker image parsing tests
python -m pytest tests/test_tag_parsing.py -v

# Update check functionality
python -m pytest tests/test_update_checks.py -v

# UI behavior tests
python -m pytest tests/test_dynamic_ui_reactive.py -v
python -m pytest tests/test_ui_field_visibility.py -v

# Unique ID generation tests
python -m pytest tests/test_unique_id_fix.py -v
```

### VS Code Test Discovery

All tests are automatically discovered by VS Code and can be run through the Testing sidebar. The test configuration is properly set up in:

- `.vscode/settings.json` - Python and pytest configuration
- `pytest.ini` - Test discovery and execution settings
- `tests/conftest.py` - Shared fixtures and Home Assistant test framework setup

## Test Results Summary

| Test File                     | Tests | Status      | Primary Focus                  |
| ----------------------------- | ----- | ----------- | ------------------------------ |
| `test_pure_logic.py`          | 24    | ✅ All Pass | Config flow logic & validation |
| `test_availability_fix.py`    | 12    | ✅ All Pass | Entity availability management |
| `test_tag_parsing.py`         | 37    | ✅ All Pass | Docker image parsing           |
| `test_update_checks.py`       | 20    | ✅ All Pass | Update check functionality     |
| `test_unique_id_fix.py`       | 8     | ✅ All Pass | Entity unique ID generation    |
| `test_ui_field_visibility.py` | 5     | ✅ All Pass | Conditional UI field display   |
| `test_dynamic_ui_reactive.py` | 4     | ✅ All Pass | Reactive UI behavior           |

**Total: 110/110 tests pass (100% success rate)**

## Test Quality & Coverage

✅ **Framework Compliance**: All tests use official Home Assistant test framework  
✅ **VS Code Integration**: Full test discovery and debugging support  
✅ **CI/CD Ready**: No external dependencies, reliable execution  
✅ **Best Practices**: Proper fixtures, mocking, and isolation  
✅ **Comprehensive Coverage**: All major integration features tested

## Implementation Details Verified

1. **Entity Management**: Proper availability states based on feature toggles
2. **Update Check System**: Complete scheduling, API handling, and caching logic
3. **Docker Integration**: Robust parsing of complex image names and registries
4. **UI Modernization**: Reactive forms with conditional field display
5. **Unique ID System**: Collision-free entity registration across configurations
6. **Error Resilience**: Graceful handling of edge cases and invalid inputs
7. **Framework Integration**: Full compatibility with Home Assistant test patterns

## Recent Cleanup (July 2025)

The test suite has been completely refactored and cleaned up:

- ✅ **Removed Duplicates**: Eliminated 57 duplicate tests from `_new` and `_old` variants
- ✅ **Deleted Obsolete Files**: Removed empty and broken test files
- ✅ **Framework Compliance**: All tests now use official Home Assistant patterns
- ✅ **VS Code Ready**: Perfect integration with VS Code testing sidebar
- ✅ **Maintainable**: Clean structure with only essential, working tests

## Development Workflow

For **new features** or **bug fixes**:

1. **Write tests first** in appropriate test file or create new one
2. **Run specific tests** during development: `python -m pytest tests/test_<feature>.py -v`
3. **Run full suite** before commit: `python -m pytest tests/ -v`
4. **Use VS Code** for interactive debugging and test exploration

## Framework Compatibility Notes

- **Home Assistant Integration**: All tests use the official `pytest-homeassistant-custom-component` framework
- **VS Code Support**: Full test discovery, debugging, and execution through the Testing sidebar
- **CI/CD Ready**: No external dependencies beyond standard HA test requirements
- **Python 3.13 Compatible**: Tested and verified with latest Python version

The test suite provides comprehensive coverage and serves as both validation and documentation for the integration's functionality.
