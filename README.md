# Logic analyzer MCP

This project provides an MCP (Message Control Protocol) server and automation interface for Saleae logic analyzers. It enables remote control, automation, and integration of Saleae Logic devices and captures, making it easy to script, manage, and analyze logic analyzer data programmatically.

## Features

- Device configuration management
- Capture configuration and execution
- Data export in various formats
- Logic file analysis and processing
- Protocol decoding and visualization
- Diagram generation and analysis
- MCP (Message Control Protocol) server integration
- Support for Logic 16 and other Logic 2 devices
- Capture file parsing and analysis using python-saleae

## Requirements

- Python 3.10 or higher
- Saleae Logic 2 software installed
- Python-saleae module
- Logic 2 device (Logic 16, Logic Pro 8, etc.)

## Installation

1. Clone the repository

2. Create and activate a virtual environment using uv:
```bash
# Create virtual environment
uv venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Unix/MacOS:
source .venv/bin/activate
```

3. Install dependencies using uv:
```bash
# Install all dependencies
uv pip install -e .
```

If you encounter any issues with dependencies, you can try installing them directly:
```bash
# Install logic2-automation from GitHub
uv pip install git+https://github.com/saleae/logic2-automation/#subdirectory=python

# Install other dependencies
uv pip install grpcio protobuf grpcio-tools saleae mcp[cli] pytest
```

Note: This project requires Python 3.10 or higher due to dependency requirements.

## Usage

### Running the MCP Server

To start the MCP server for remote control:

```bash
# Using uv (recommended)
uv --directory <project_path> run -m src.run_mcp_server
```

Note: When using `uv`, make sure you have it installed and in your PATH. The `--directory` argument should point to the root directory of the project.

## Troubleshooting & Important Notes

- **Logic Software Must Be Running:**
  - Before using this automation interface, ensure that the Saleae Logic software is already running on your system. The automation scripts will attempt to connect to the running instance.
  - If the software is not running, the script may fail to connect, or may launch a new instance in simulation mode (which will not detect your real device).

- **Enable Scripting Socket Server:**
  - In the Logic software, go to `Options` > `Preferences` (or `Edit` > `Preferences`), and ensure that the "Enable scripting socket server" option is checked.
  - The default port is usually 10429. If you change this, update your scripts accordingly.
  - If the scripting server is not enabled, the Python API will not be able to communicate with Logic, and you will see connection errors.

- **Device Not Detected:**
  - Make sure your Logic device is connected to your computer and recognized by the Logic software before running any scripts.
  - If the device is not detected, check your USB connection and try restarting the Logic software.

- **Architecture Compatibility:**
  - Ensure that both the Logic software and your Python environment are either both 32-bit or both 64-bit. Mismatched architectures can cause connection failures.

- **Permissions:**
  - On some systems, you may need to run the Logic software and/or your Python script with administrator privileges to allow socket communication.

- **Supported Versions:**
  - This project is designed for Saleae Logic 1.x/2.x automation. Some features may only be available in Logic 2.x with the appropriate automation API installed.

## Compatibility & Tested Version

This project is tested with [Saleae Logic 1.2.40 for Windows](https://downloads.saleae.com/logic/1.2.40/Logic%201.2.40%20(Windows).zip).

- Please use this version for best compatibility.
- Other versions may work, but are not guaranteed or officially supported by this project.

### Note on Capture File Formats

- **.logicdata format** is the recommended and best-supported file format for captures. All automation and parsing features are designed to work reliably with `.logicdata` files.
- **.sal files** (used by some older or alternative Saleae software) are currently known to have bugs and compatibility issues. Automated conversion or processing of `.sal` files may fail or require manual fixes. For best results, always use `.logicdata` format for your captures.

## API Reference

### SaleaeController

The main controller class that provides high-level access to Logic 2 functionality.

#### Device Configuration Methods:

- `create_device_config(name: str, digital_channels: List[int], digital_sample_rate: int, analog_channels: Optional[List[int]] = None, analog_sample_rate: Optional[int] = None, digital_threshold_volts: Optional[float] = None) -> str`
  - Creates a new device configuration with specified channels and sample rates
  - Returns the configuration name

- `get_device_config(name: str) -> Optional[LogicDeviceConfiguration]`
  - Retrieves a device configuration by name
  - Returns None if not found

- `list_device_configs() -> List[str]`
  - Lists all available device configuration names

- `remove_device_config(name: str) -> bool`
  - Removes a device configuration
  - Returns True if successful, False if not found

#### Capture Configuration Methods:

- `create_capture_config(name: str, duration_seconds: float, buffer_size_megabytes: Optional[int] = None) -> str`
  - Creates a new capture configuration with specified duration
  - Returns the configuration name

- `get_capture_config(name: str) -> Optional[CaptureConfiguration]`
  - Retrieves a capture configuration by name
  - Returns None if not found

- `list_capture_configs() -> List[str]`
  - Lists all available capture configuration names

- `remove_capture_config(name: str) -> bool`
  - Removes a capture configuration
  - Returns True if successful, False if not found


## Configurations:

### Claude configuration (with uv run):
```json
{
    "mcpServers": {
        "logic-analyzer-ai-mcp": {
            "type": "stdio",
            "command": "uv",
            "args": [
                "--directory",
                "<path to folder>",
                "run",
                "-m",
                "src.run_mcp_server"
            ]
        }
    }
}
```

### Claude configuration (direct usage):
```json
{
    "mcpServers": {
        "logic-analyzer-ai-mcp": {
            "type": "stdio",
            "command": "python",
            "args": [
                "<path to folder>\\src\\run_mcp_server.py"
            ]
        }
    }
}
```


### Claude configuration (with uv run):
```json
{
    "mcpServers": {
        "logic-analyzer-ai-mcp": {
            "type": "stdio",
            "command": "uv",
            "args": [
                "--directory",
                "<path to folder>",
                "run",
                "-m",
                "src.run_mcp_server"
            ]
        }
    }
}
```