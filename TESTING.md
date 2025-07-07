# Testing Guide

## Test Setup

This project uses pytest for testing. The test suite validates core functionality of the Portainer Home Assistant custom component.

## Quick Start

### Prerequisites

1. **Create virtual environment** (recommended):

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

2. **Install dependencies**:

```bash
pip install -r requirements_test.txt
```

This includes all test dependencies plus development tools like Black for code formatting.

### Code Formatting

Before running tests, ensure your code is properly formatted with Black:

```bash
# Format all code
black custom_components/ tests/

# Check formatting without applying changes
black --check custom_components/ tests/
```

### Run All Tests

```bash
# Run all 110 tests (all passing)
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=custom_components.portainer --cov-report=html
```

### Run Specific Test Categories

```bash
# Entity availability tests (12 tests) ✅
python -m pytest tests/test_availability_fix.py -v

# Dynamic UI behavior tests (4 tests) ✅
python -m pytest tests/test_dynamic_ui_reactive.py -v

# Pure logic tests (24 tests) ✅
python -m pytest tests/test_pure_logic.py -v

# Tag parsing tests (37 tests) ✅
python -m pytest tests/test_tag_parsing.py -v

# UI field visibility tests (5 tests) ✅
python -m pytest tests/test_ui_field_visibility.py -v

# Unique ID generation tests (8 tests) ✅
python -m pytest tests/test_unique_id_fix.py -v

# Update check tests (20 tests) ✅
python -m pytest tests/test_update_checks.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=custom_components/portainer --cov-report=html
```

## Test Status

### All Tests Passing (110/110) ✅

**Current Test Files (All Fully Working):**

- ✅ `test_availability_fix.py` - Entity availability management (12 tests)
- ✅ `test_dynamic_ui_reactive.py` - Dynamic UI behavior (4 tests)
- ✅ `test_pure_logic.py` - Core config flow logic (24 tests)
- ✅ `test_tag_parsing.py` - Docker image parsing (37 tests)
- ✅ `test_ui_field_visibility.py` - UI field visibility (5 tests)
- ✅ `test_unique_id_fix.py` - Unique ID generation (8 tests)
- ✅ `test_update_checks.py` - Update check logic (20 tests)

**Key Improvements Made:**

- All tests use `pytest-homeassistant-custom-component` framework
- Removed all obsolete and duplicate test files
- Clean project structure with only essential, working tests
- Perfect VS Code integration with test discovery
- 100% test success rate
- Comprehensive coverage of all major integration features

## Summary

**Cleanup and Refactoring Complete! ✅**

All unit tests have been successfully refactored and cleaned up. The test suite now:

- **110/110 tests passing** (100% success rate)
- Uses proper Home Assistant fixtures and mocks
- Follows pytest-homeassistant-custom-component conventions
- Has clean imports without sys.path hacks
- No duplicate or obsolete files
- Perfect VS Code integration
- Ready for production and CI/CD

All obsolete `_old` test files and duplicate code have been removed, leaving only essential, framework-compliant tests.

## VS Code Integration

### Setup für VS Code Test Discovery

1. **Stelle sicher, dass das virtuelle Environment aktiv ist:**

   - Öffne VS Code Terminal (` Ctrl+Shift+``  `)
   - Das Prompt sollte `(.venv)` zeigen
   - Falls nicht: `source .venv/bin/activate`

2. **Python Interpreter setzen:**

   - `Ctrl+Shift+P` → "Python: Select Interpreter"
   - Wähle `./.venv/bin/python`

3. **Tests in VS Code anzeigen:**

   - Öffne die Test-Ansicht (`Ctrl+Shift+P` → "Test: Focus on Test Explorer View")
   - Oder klicke auf das Test-Symbol in der Seitenleiste (🧪)
   - Falls Tests nicht erscheinen: `Ctrl+Shift+P` → "Test: Refresh Tests"

4. **Manuelle Test Discovery (falls nötig):**
   ```bash
   # Im VS Code Terminal ausführen:
   python -m pytest --collect-only tests/ -q
   ```

### VS Code Test-Befehle

- **Alle Tests ausführen:** `Ctrl+Shift+P` → "Test: Run All Tests"
- **Einzelnen Test ausführen:** Klick auf ▶️ neben dem Test
- **Test debuggen:** Klick auf 🐛 neben dem Test
- **Tests aktualisieren:** `Ctrl+Shift+P` → "Test: Refresh Tests"

### Troubleshooting

Wenn Tests in VS Code nicht erscheinen:

1. Prüfe Python Interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter"
2. Prüfe Test-Konfiguration in `.vscode/settings.json`
3. Restarte VS Code: `Ctrl+Shift+P` → "Developer: Reload Window"
4. Manuell testen: `python -m pytest tests/ --tb=short`

## Summary

**Refactoring Complete! ✅**

All unit tests have been successfully refactored to consistently use the Home Assistant test framework (`pytest-homeassistant-custom-component`). The test suite now:

- **110/110 tests passing** (100% success rate)
- Uses proper Home Assistant fixtures and mocks
- Follows pytest-homeassistant-custom-component conventions
- Has clean imports without sys.path hacks
- Maintains all original test functionality
- Is ready for CI/CD integration

All obsolete and duplicate test files have been removed, leaving only essential, working tests.

## Test Structure

```
tests/
├── conftest.py                   # HA test framework configuration
├── test_availability_fix.py      # Entity availability (12 tests) ✅
├── test_dynamic_ui_reactive.py   # Dynamic UI behavior (4 tests) ✅
├── test_pure_logic.py            # Core config flow logic (24 tests) ✅
├── test_tag_parsing.py           # Docker image parsing (37 tests) ✅
├── test_ui_field_visibility.py   # UI field visibility (5 tests) ✅
├── test_unique_id_fix.py         # Unique ID generation (8 tests) ✅
└── test_update_checks.py         # Update check logic (20 tests) ✅
```

## Writing New Tests

Follow the existing patterns:

- Use pytest fixtures for setup
- Test both positive and negative cases
- Mock external dependencies (API calls)
- Use descriptive test names

Example:

```python
def test_parse_image_name_with_registry():
    """Test parsing image names with registry prefixes."""
    coordinator = PortainerCoordinator.__new__(PortainerCoordinator)
    repo, tag = coordinator._parse_image_name("registry.com/app:v1.0")
    assert repo == "registry.com/app"
    assert tag == "v1.0"
```
