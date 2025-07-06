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
# Run all 55 tests
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=custom_components.portainer --cov-report=html
```

### Run Specific Test Categories

```bash
# Tag parsing tests (37 tests) ✅
python -m pytest tests/test_tag_parsing.py -v

# Update check tests (18 tests) ✅
python -m pytest tests/test_update_checks.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=custom_components/portainer --cov-report=html
```

## Test Status

### Working Tests (30/55)

- ✅ Docker image tag parsing
- ✅ Image name normalization
- ✅ Registry handling
- ✅ Digest removal
- ✅ Basic coordinator functionality

### Tests Needing Fixes (25/55)

- 🔧 Update check logic tests (API signature mismatch)
- 🔧 Cache invalidation tests (method naming)
- 🔧 Some edge cases in tag parsing

## VS Code Integration

Use the "Run Tests" task in VS Code:

- Open Command Palette (`Ctrl+Shift+P`)
- Type "Tasks: Run Task"
- Select "Run Tests"

## Test Structure

```
tests/
├── conftest.py          # Test configuration and fixtures
├── test_tag_parsing.py  # Docker image name parsing tests
└── test_update_checks.py # Update check logic tests
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
