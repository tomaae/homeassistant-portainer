# Portainer integration for Home Assistant

![GitHub release (latest by date)](https://img.shields.io/github/v/release/tomaae/homeassistant-portainer?style=plastic)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=plastic)](https://github.com/hacs/integration)
![Project Stage](https://img.shields.io/badge/project%20stage-development-yellow.svg?style=plastic)
![GitHub all releases](https://img.shields.io/github/downloads/tomaae/homeassistant-portainer/total?style=plastic)

![GitHub commits since latest release](https://img.shields.io/github/commits-since/tomaae/homeassistant-portainer/latest?style=plastic)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/tomaae/homeassistant-portainer?style=plastic)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/tomaae/homeassistant-portainer/ci.yml?style=plastic)

[![Help localize](https://img.shields.io/badge/lokalise-join-green?style=plastic&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAyhpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNi1jMTQ1IDc5LjE2MzQ5OSwgMjAxOC8wOC8xMy0xNjo0MDoyMiAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6REVCNzgzOEY4NDYxMTFFQUIyMEY4Njc0NzVDOUZFMkMiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6REVCNzgzOEU4NDYxMTFFQUIyMEY4Njc0NzVDOUZFMkMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENDIDIwMTcgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDozN0ZDRUY4Rjc0M0UxMUU3QUQ2MDg4M0Q0MkE0NjNCNSIgc3RSZWY6ZG9jdW1lbnRJRD0ieG1wLmRpZDozN0ZDRUY5MDc0M0UxMUU3QUQ2MDg4M0Q0MkE0NjNCNSIvPiA8L3JkZjpEZXNjcmlwdGlvbj4gPC9yZGY6UkRGPiA8L3g6eG1wbWV0YT4gPD94cGFja2V0IGVuZD0iciI/Pjs1zyIAAABVSURBVHjaYvz//z8DOYCJgUxAtkYW9+mXyXIrI7l+ZGHc0k5nGxkupdHZxve1yQR1CjbPZURXh9dGoGJZIPUI2QC4JEgjIfyuJuk/uhgj3dMqQIABAPEGTZ/+h0kEAAAAAElFTkSuQmCC)](https://app.lokalise.com/public/892665226456f113e0a814.16864793/)

![English](https://raw.githubusercontent.com/tomaae/homeassistant-mikrotik_router/master/docs/assets/images/flags/us.png)

![Portainer Logo](https://raw.githubusercontent.com/tomaae/homeassistant-portainer/master/docs/assets/images/ui/logo.png)

Monitor and control Portainer from Home Assistant.

Features:

- List Endpoints
- List Containers

# Features

## Endpoints

List of Portainer endpoints.

![Endpoints](https://raw.githubusercontent.com/tomaae/homeassistant-portainer/master/docs/assets/images/ui/endpoints.png)

## Containers

List of containers.

![Containers](https://raw.githubusercontent.com/tomaae/homeassistant-portainer/master/docs/assets/images/ui/containers.png)

## Update Check Feature

The integration supports checking for available updates for your containers via Docker Hub and GitHub registries.

- **Check update**: This option is **disabled by default**. To use update checks, you must enable the option in the integration settings (`Configuration -> Integrations -> Portainer -> Configure`).
- **Update check time**: You can set the hour of day when the automatic update check should run. The update cycle is every 24 hours at the configured time.
- **Update check button and sensor**: Both the update check button ("Force update check") and the update check sensor are **disabled by default** in the Home Assistant entity registry. You must enable them manually under `Settings -> Devices & Services -> Entities` to use them.
- **Force update**: The update check button allows you to trigger an immediate update check outside the regular schedule. **Note:** Most registries (Docker Hub, GitHub) have rate limits. Excessive use of the force update button may result in temporary blocks or errors from the registry.
- **Supported registries**: Currently, Docker Hub and GitHub Container Registry are supported for update checks.

You can view the update status and details in the sensor attributes. The button entity can be used to trigger a manual check, but please use it responsibly to avoid hitting registry rate limits.

### Status Codes

The update check sensor and button use the following status codes in their state and attributes:

| Status Code | Meaning                                                 |
| ----------- | ------------------------------------------------------- |
| 0           | No update available (up to date)                        |
| 1           | Update available                                        |
| 2           | Update status not yet checked                           |
| 401         | Unauthorized (registry credentials required or invalid) |
| 404         | Image not found on registry                             |
| 429         | Registry rate limit reached                             |
| 500         | Registry/internal error                                 |

The sensor attributes also include a human-readable `update_status_description` for each code. For details on errors or rate limits, see the sensor attributes.

# Install integration

This integration is distributed using [HACS](https://hacs.xyz/).

You can find it under "Integrations", named "Portainer".

## Get portainer access token

1. Login into your portainer instance
2. Click you username at top right and select "My Account"
3. Under "Access tokens", click "Add access token"
4. Enter name for your access token (can be anything, for example "homeassistant")
5. Copy displayed access token for use in integration setup

## Setup integration

Setup this integration for your Portainer in Home Assistant via `Configuration -> Integrations -> Add -> Portainer`.
You can add this integration several times for different portainer instances.

- "Name of the integration" - Friendly name for this Portainer instance
- "Host" - Use hostname or IP and port (example: portainer.domain.tld or 192.168.0.2:9000)
- "Access token" - Use access token from previous step
- "Use SSL" - Connect to portainer using SSL
- "Verify SSL certificate" - Validate SSL certificate (must be trusted certificate)

## Configuration

After setup, you can configure custom attributes and options for each Portainer entry via `Configuration -> Integrations -> Portainer -> Configure`.

### Supported options:

- **Check update**: Enable or disable the update check feature (see above for details).
- **Update check time**: Set the hour of day for the daily update check.
- **Health check**: Checks if the container is running correctly by executing a defined command.
- **Restart policy**: Defines how and when the container restarts after stopping.

![Configuration](https://raw.githubusercontent.com/tomaae/homeassistant-portainer/master/docs/assets/images/ui/options.png)

# Development

## Software Development

### Prerequisites

- Python 3.11 or higher
- Git
- Visual Studio Code (recommended)

### Setting up the Development Environment

#### 1. Clone the Repository

```bash
git clone https://github.com/tomaae/homeassistant-portainer.git
cd homeassistant-portainer
```

#### 2. Create a Virtual Environment

It's highly recommended to use a virtual environment to isolate dependencies:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install development and testing dependencies
pip install -r requirements_test.txt
```

#### 4. Install Development Tools (Optional)

```bash
# Install pre-commit hooks for code quality
pre-commit install
```

### Code Formatting

This project uses Black for code formatting. All code must be Black-formatted before committing. VS Code is configured to auto-format on save if you use the provided settings.

```bash
# Format all Python files
black custom_components/ tests/

# Check formatting without making changes
black --check custom_components/ tests/
```

### Running Tests

#### Command Line

```bash
# Run all tests
python -m pytest

# Run tests with verbose output
python -m pytest -v

# Run tests with coverage report
python -m pytest --cov=custom_components.portainer --cov-report=html

# Run specific test file
python -m pytest tests/test_tag_parsing.py

# Run specific test
python -m pytest tests/test_tag_parsing.py::TestDockerImageTagParsing::test_parse_image_name
```

#### Visual Studio Code Integration

##### 1. Install Extensions

Install the following VS Code extensions:

- **Python** (ms-python.python)
- **Python Test Explorer** (or use built-in testing)

##### 2. Configure VS Code Settings

Create or update `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": ["tests"],
  "python.testing.autoTestDiscoverOnSaveEnabled": true,
  "python.terminal.activateEnvironment": true,
  "editor.formatOnSave": true,
  "python.formatting.provider": "black"
}
```

##### 3. Activate Tests in VS Code

1. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
2. Run `Python: Select Interpreter`
3. Choose `./.venv/bin/python`
4. Run `Test: Refresh Tests` to discover tests
5. Open the Test Explorer (`Ctrl+Shift+T` / `Cmd+Shift+T`)

You should now see all 110 tests organized by file and class in the Test Explorer.

##### 4. Running Tests in VS Code

- **Run all tests**: Click the play button at the top of Test Explorer
- **Run specific test**: Click the play button next to any test
- **Debug test**: Right-click on a test and select "Debug Test"
- **View test output**: Click on any test to see results and output

### Test Structure

```
tests/
├── test_availability_fix.py      # Entity availability management (enabled/disabled states)
├── test_dynamic_ui_reactive.py   # Dynamic UI behavior
├── test_pure_logic.py            # Core config flow logic and validation
├── test_tag_parsing.py           # Docker image name parsing
├── test_ui_field_visibility.py   # Conditional field display
├── test_unique_id_fix.py         # Entity unique ID generation
└── test_update_checks.py         # Container update logic and caching
```

### Development Workflow

1. **Create a feature branch**: `git checkout -b feature/your-feature`
2. **Make changes** to the code
3. **Format code**: Use Black to ensure consistent code style
4. **Run tests**: `python -m pytest` to ensure nothing breaks
5. **Commit changes**: `git commit -m "Description of changes"`
6. **Push and create PR**: `git push origin feature/your-feature`

#### Code Formatting with Black

This project uses [Black](https://black.readthedocs.io/) for consistent code formatting.

```bash
# Format all Python files
black custom_components/ tests/

# Check if files need formatting (without applying changes)
black --check custom_components/ tests/

# Format specific file
black custom_components/portainer/coordinator.py
```

**Important**: All code must be Black-formatted before committing. VS Code is configured to auto-format on save if you use the provided settings.

### Debugging

Add breakpoints in VS Code and use the debug configuration for pytest:

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: pytest",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/", "-v"],
      "console": "integratedTerminal",
      "python": "./.venv/bin/python",
      "cwd": "${workspaceFolder}"
    }
  ]
}
```

### Current Test Coverage

- **Total Tests**: 121
- **Entity Availability Tests**: Entity enabled/disabled states
- **Static UI Tests**: Static UI behavior
- **Pure Logic Tests**: Config flow logic and validation
- **Tag Parsing Tests**: Docker image name parsing
- **UI Field Visibility Tests**: Conditional field display
- **Unique ID Tests**: Entity unique ID generation
- **Update Check Tests**: Container update logic and caching
- **Success Rate**: 100% ✅

## Translation

To help out with the translation you need an account on Lokalise, the easiest way to get one is to [click here](https://lokalise.com/login/) then select "Log in with GitHub".
After you have created your account [click here to join Portainer project on Lokalise](https://app.lokalise.com/public/892665226456f113e0a814.16864793/).

If you want to add translations for a language that is not listed please [open a Feature request](https://github.com/tomaae/homeassistant-portainer/issues/new?labels=enhancement&title=%5BLokalise%5D%20Add%20new%20translations%20language).

## Enabling debug

To enable debug for Portainer integration, add following to your configuration.yaml:

```
logger:
  default: info
  logs:
    custom_components.portainer: debug
```
