# Logic Analyzer AI MCP

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server for interfacing with **Saleae Logic** analyzers. This tool allows AI assistants (like Claude) to control hardware logic analyzers, capture signals, and export data for analysis.

## Features

- **Device Management**: List connected devices, configure sample rates and channels.
- **Automation**: Start and stop captures programmatically.
- **Data Export**: Export captures to CSV/binary formats.
- **Analysis**: Perform basic signal analysis (frequency, duty cycle, analog stats) directly via MCP.
- **Logic 2 Integration**: Leverages the Saleae Logic 2 automation API for modern device support (Logic 8/16, Pro 8/16).
- **Adaptive Configuration**: Works with fixed-voltage devices (like Logic 8) by correctly handling threshold settings.

## Prerequisites

1.  **Saleae Logic 2 Software**: Must be installed and running.
    *   [Download Logic 2](https://www.saleae.com/downloads/)
2.  **Enable Automation**:
    *   Open Logic 2.
    *   Go to **Preferences** > **Salese Logic 2** (or "Automation").
    *   Enable **"Enable scripting socket server"**.
    *   Keep the default port **10430**.

## Installation

This project uses `uv` for dependency management, but standard `pip` works too.

### Using `uv` (Recommended)

1.  Clone the repository:
    ```bash
    git clone https://github.com/wegitor/logic-analyzer-ai-mcp.git
    cd logic-analyzer-ai-mcp
    ```

2.  Create a virtual environment and sync dependencies:
    ```bash
    uv venv
    uv sync
    ```

3.  (Optional) Install manually if not syncing:
    ```bash
    uv pip install -e .
    ```

## Usage

### Running the MCP Server manually

To run the server and see available tools:

```bash
# Activate virtual environment first
.venv\Scripts\activate

# Run the server with Logic 2 automation enabled
python -m src.logic_analyzer_mcp --logic2
```

### Configuration for Claude Desktop

To use this with Claude Desktop, add the following to your config file:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "saleae_logic": {
      "command": "c:\\path\\to\\logic-analyzer-ai-mcp\\.venv\\Scripts\\python.exe",
      "args": [
        "c:\\path\\to\\logic-analyzer-ai-mcp\\src\\logic_analyzer_mcp.py",
        "--logic2"
      ]
    }
  }
}
```
*Note: Replace `c:\\path\\to\\...` with the actual absolute path to your project folder.*

## Available Tools

Once connected, the AI assistant will have access to tools like:

- `logic2_reconnect`: Connect to the running Saleae software.
- `get_available_devices`: List connected hardware or simulation devices.
- `create_device_config`: Set up channels and sample rates.
- `capture_and_analyze_digital`: One-shot capture + frequency/duty cycle analysis.
- `capture_and_analyze_analog`: One-shot capture + voltage statistics.
- `start_capture` / `wait_capture` / `save_capture`: Granular control over the capture workflow.
- `start_capture_with_trigger`: Wait for a digital event (e.g. Rising Edge) before capturing.
- `add_protocol_analyzer`: Add decoders like Serial, I2C, SPI to the capture.
- `export_analyzer_data`: Export decoded text data to CSV.

## Advanced Usage Examples

### Using Digital Triggers
To capture only when a specific event happens:
1.  Configure device (`create_device_config`).
2.  Start trigger capture:
    ```python
    # Example: Wait for Rising Edge on Channel 0, then record 1 second
    start_capture_with_trigger(
        device_config_name="my_config",
        trigger_channel_index=0,
        trigger_type="RISING",
        after_trigger_seconds=1.0
    )
    ```

### Protocol Decoding (e.g. Serial)
To decode UART/Serial data and export the text:
1.  Perform a capture (standard or triggered).
2.  Add an analyzer:
    ```python
    add_protocol_analyzer(
        name="Async Serial",
        label="MySerial",
        settings={
            "Input Channel": 0,
            "Bit Rate": 115200
        }
    )
    ```
3.  Export the decoded table:
    ```python
    export_analyzer_data(
        filepath="C:\\temp\\serial_data.csv",
        analyzer_label="MySerial"
    )
    ```

## Troubleshooting

- **"Connection Refused"**: Ensure Logic 2 is running and the scripting server is enabled on port 10430.
- **"Threshold Error"**: If using Logic 8 (which doesn't support variable thresholds), ensure you don't pass a `digital_threshold_volts` value (the tool handles this automatically now).

## License

[MIT](LICENSE)