# Contributing to Portainer Integration

Thank you for your interest in contributing to the Portainer Home Assistant integration!

## Development Setup

### Quick Start

```bash
# 1. Clone and enter directory
git clone https://github.com/tomaae/homeassistant-portainer.git
cd homeassistant-portainer

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements_test.txt

# 4. Run tests to verify setup
python -m pytest -v
```

## Code Standards

### Formatting

- Use **Black** for code formatting: `black custom_components/ tests/`
- Line length: 88 characters (Black default)
- Follow PEP 8 conventions

### Testing

- Write tests for all new functionality
- Maintain 100% test success rate
- Use descriptive test names and docstrings
- Current test coverage: 55 tests (37 tag parsing + 18 update logic)

### Type Hints

- Use type hints for all function parameters and return values
- Import types from `typing` module when needed

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all public methods
- Use clear, descriptive variable names

## Testing Guidelines

### Running Tests

```bash
# All tests
python -m pytest

# Specific test file
python -m pytest tests/test_tag_parsing.py

# With coverage
python -m pytest --cov=custom_components.portainer --cov-report=html
```

### Test Structure

- `tests/test_tag_parsing.py`: Docker image name parsing logic
- `tests/test_update_checks.py`: Container update check functionality

### Writing New Tests

1. Place tests in appropriate file based on functionality
2. Use descriptive test class and method names
3. Include docstrings explaining what the test validates
4. Use pytest fixtures for common setup
5. Mock external dependencies (API calls, Home Assistant core)

## Submitting Changes

### Workflow

1. **Fork** the repository
2. **Create feature branch**: `git checkout -b feature/your-feature-name`
3. **Make changes** with tests
4. **Run tests**: `python -m pytest`
5. **Format code**: `black custom_components/ tests/`
6. **Commit**: `git commit -m "Add your feature description"`
7. **Push**: `git push origin feature/your-feature-name`
8. **Create Pull Request**

### Pull Request Guidelines

- Clear description of changes
- Reference any related issues
- Ensure all tests pass
- Update documentation if needed
- Add tests for new functionality

## Development Tools

### Recommended VS Code Extensions

- Python (ms-python.python)
- Black Formatter (ms-python.black-formatter)
- Pylint (ms-python.pylint)
- GitLens (eamodio.gitlens)

### Pre-commit Hooks (Optional)

```bash
pip install pre-commit
pre-commit install
```

This will automatically format code and run basic checks before each commit.

## Architecture Overview

### Key Components

- `coordinator.py`: Main data coordinator handling API communication
- `sensor.py`: Container sensor entities
- `button.py`: Container action buttons (start/stop/restart)
- `config_flow.py`: Integration setup flow

### Key Features Tested

- **Docker Image Tag Parsing**: Complex registry/tag parsing logic
- **Update Check Logic**: Container update detection and caching
- **API Communication**: Portainer API integration
- **Error Handling**: Graceful handling of API failures

## Getting Help

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Documentation**: Check README.md and inline code documentation

## Code of Conduct

Please be respectful and constructive in all interactions. This project follows the standard open source community guidelines.
