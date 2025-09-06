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
# Run all tests (all passing)
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=custom_components.portainer --cov-report=html
```

### Run Specific Test Categories

```bash
# Entity availability tests
python -m pytest tests/test_availability_fix.py -v

# Static UI behavior tests
python -m pytest tests/test_static_ui.py -v

# Pure logic tests
python -m pytest tests/test_pure_logic.py -v

# Tag parsing tests
python -m pytest tests/test_tag_parsing.py -v

# UI field visibility tests
python -m pytest tests/test_ui_field_visibility.py -v

# Unique ID generation tests
python -m pytest tests/test_unique_id_fix.py -v

# Update check tests
python -m pytest tests/test_update_checks.py -v
```

### Run with Coverage

```bash
python -m pytest tests/ --cov=custom_components.portainer --cov-report=html
```

## Test Status

### All Tests Passing

**Current Test Files (All Fully Working):**

- `test_availability_fix.py` - Entity availability management
- `test_static_ui.py` - Static UI behavior
- `test_pure_logic.py` - Core config flow logic
- `test_tag_parsing.py` - Docker image parsing
- `test_ui_field_visibility.py` - UI field visibility
- `test_unique_id_fix.py` - Unique ID generation
- `test_update_checks.py` - Update check logic

**Key Improvements Made:**

- All tests use `pytest-homeassistant-custom-component` framework
- Clean project structure with only essential, working tests
- Full VS Code integration with test discovery
- 100% test success rate
- Comprehensive coverage of all major integration features

## VS Code Integration

### VS Code Test Discovery Setup

1. **Ensure the virtual environment is active:**

   - Open VS Code Terminal (`Ctrl+Shift+\``)
   - The prompt should show `(.venv)`
   - If not: `source .venv/bin/activate`

2. **Set Python Interpreter:**

   - `Ctrl+Shift+P` → "Python: Select Interpreter"
   - Choose `./.venv/bin/python`

3. **Show tests in VS Code:**

   - Open the Test Explorer (`Ctrl+Shift+P` → "Test: Focus on Test Explorer View")
   - Or click the test icon in the sidebar (🧪)
   - If tests do not appear: `Ctrl+Shift+P` → "Test: Refresh Tests"

4. **Manual test discovery (if needed):**
   ```bash
   python -m pytest --collect-only tests/ -q
   ```

### VS Code Test Commands

- **Run all tests:** `Ctrl+Shift+P` → "Test: Run All Tests"
- **Run single test:** Click ▶️ next to the test
- **Debug test:** Click 🐛 next to the test
- **Refresh tests:** `Ctrl+Shift+P` → "Test: Refresh Tests"

### Troubleshooting

If tests do not appear in VS Code:

1. Check Python Interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter"
2. Check test configuration in `.vscode/settings.json`
3. Restart VS Code: `Ctrl+Shift+P` → "Developer: Reload Window"
4. Run manually: `python -m pytest tests/ --tb=short`

## Summary

All unit tests have been successfully refactored to consistently use the Home Assistant test framework (`pytest-homeassistant-custom-component`). The test suite now:

- 100% test success rate
- Uses proper Home Assistant fixtures and mocks
- Follows pytest-homeassistant-custom-component conventions
- Has clean imports without sys.path hacks
- Maintains all original test functionality
- Is ready for CI/CD integration
- Uses a static UI approach where all fields are always visible

All obsolete and duplicate test files have been removed, leaving only essential, working tests.

## Test Structure

```
tests/
├── conftest.py                   # HA test framework configuration
├── test_availability_fix.py      # Entity availability (12 tests) ✅
├── test_static_ui.py            # Static UI behavior (5 tests) ✅
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
