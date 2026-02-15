from mcp.server.fastmcp import FastMCP, Context
from typing import Optional, Dict, Any, List, Union
import os
import json
import time
import logging
import csv
import statistics

logger = logging.getLogger(__name__)

def setup_mcp_tools_experimental(mcp: FastMCP, controller=None) -> None:
    """Setup Logic 2 automation MCP tools."""

    @mcp.tool("logic2_reconnect")
    def logic2_reconnect(ctx: Context, port: int = 10430) -> Dict[str, Any]:
        """Connect (or reconnect) to Logic 2 automation server.
        Must be called before any capture or device query.
        Logic 2 must be running with automation enabled (Preferences > Enable scripting API)."""
        try:
            ok = controller.reconnect(port=port)
            if ok:
                return {"status": "success", "message": f"Connected to Logic 2 on port {port}"}
            return {"status": "error", "message": "Failed to connect. Is Logic 2 running with automation enabled?"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool("create_device_config")
    def create_device_config(ctx: Context, name: str, digital_channels: List[int],
                            digital_sample_rate: int, analog_channels: Optional[List[int]] = None,
                            analog_sample_rate: Optional[int] = None,
                            digital_threshold_volts: Optional[float] = None) -> Dict[str, Any]:
        """Create a new device configuration for Saleae Logic 2."""
        try:
            n = controller.create_device_config(name=name, digital_channels=digital_channels,
                digital_sample_rate=digital_sample_rate, analog_channels=analog_channels,
                analog_sample_rate=analog_sample_rate, digital_threshold_volts=digital_threshold_volts)
            return {"status": "success", "config": n}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool("create_capture_config")
    def create_capture_config(ctx: Context, name: str, duration_seconds: float,
                            buffer_size_megabytes: Optional[int] = None) -> Dict[str, Any]:
        """Create a new capture configuration for Saleae Logic 2."""
        try:
            n = controller.create_capture_config(name=name, duration_seconds=duration_seconds,
                buffer_size_megabytes=buffer_size_megabytes)
            return {"status": "success", "config": n}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool("list_device_configs")
    def list_device_configs(ctx: Context) -> Dict[str, Any]:
        """List all available device configurations."""
        return {"status": "success", "configs": controller.list_device_configs()}

    @mcp.tool("list_capture_configs")
    def list_capture_configs(ctx: Context) -> Dict[str, Any]:
        """List all available capture configurations."""
        return {"status": "success", "configs": controller.list_capture_configs()}

    @mcp.tool("remove_device_config")
    def remove_device_config(ctx: Context, name: str) -> Dict[str, Any]:
        """Remove a device configuration."""
        ok = controller.remove_device_config(name)
        return {"status": "success" if ok else "error"}

    @mcp.tool("remove_capture_config")
    def remove_capture_config(ctx: Context, name: str) -> Dict[str, Any]:
        """Remove a capture configuration."""
        ok = controller.remove_capture_config(name)
        return {"status": "success" if ok else "error"}

    @mcp.tool("get_available_devices")
    def get_available_devices(ctx: Context) -> Dict[str, Any]:
        """Get list of available Saleae Logic devices."""
        try:
            return {"status": "success", "devices": controller.get_available_devices()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool("find_device_by_type")
    def find_device_by_type(ctx: Context, device_type: str) -> Dict[str, Any]:
        """Find a Saleae Logic device by its type."""
        try:
            from saleae.automation import DeviceType
            d = controller.find_device_by_type(DeviceType[device_type])
            if d:
                return {"status": "success", "device": d}
            return {"status": "error", "message": f"No device of type {device_type}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    # ── Capture Workflow ────────────────────────────────────────

    @mcp.tool("start_capture")
    def start_capture(ctx: Context, device_config_name: str,
                     capture_config_name: str,
                     device_id: Optional[str] = None) -> Dict[str, Any]:
        """Start a capture using named device and capture configurations."""
        try:
            controller.start_capture(device_config_name, capture_config_name, device_id)
            return {"status": "success", "message": "Capture started"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool("wait_capture")
    def wait_capture(ctx: Context) -> Dict[str, Any]:
        """Wait for the active capture to complete."""
        try:
            controller.wait_capture()
            return {"status": "success", "message": "Capture complete"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool("save_capture")
    def save_capture(ctx: Context, filepath: str) -> Dict[str, Any]:
        """Save the active capture to a .sal file."""
        try:
            os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
            controller.save_capture(filepath)
            return {"status": "success", "filepath": filepath}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool("close_capture")
    def close_capture(ctx: Context) -> Dict[str, Any]:
        """Close the active capture and free resources."""
        try:
            controller.close_capture()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool("export_raw_data_csv")
    def export_raw_data_csv(ctx: Context, directory: str,
                           analog_channels: Optional[List[int]] = None,
                           digital_channels: Optional[List[int]] = None) -> Dict[str, Any]:
        """Export raw capture data to CSV. Requires active completed capture."""
        try:
            if controller._active_capture is None:
                return {"status": "error", "message": "No active capture."}
            os.makedirs(directory, exist_ok=True)
            controller._active_capture.export_raw_data_csv(
                directory=directory,
                analog_channels=analog_channels,
                digital_channels=digital_channels)
            files = os.listdir(directory)
            return {"status": "success", "directory": directory, "files": files}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    # ── One-Shot Capture + Analyze Analog ───────────────────────

    @mcp.tool("capture_and_analyze_analog")
    def capture_and_analyze_analog(ctx: Context,
                                   analog_channels: List[int],
                                   duration_seconds: float,
                                   sample_rate: int = 625000,
                                   output_directory: Optional[str] = None) -> Dict[str, Any]:
        """One-shot: capture and analyze analog channels.
        Returns min/max/mean/stdev/peak-to-peak for each channel.

        Args:
            analog_channels: e.g. [0] or [0,1]
            duration_seconds: capture length in seconds
            sample_rate: analog sample rate in S/s (default 625000)
            output_directory: where to save CSV (default: temp dir)
        """
        try:
            controller._ensure_manager()
            from saleae.automation import (
                LogicDeviceConfiguration, CaptureConfiguration, TimedCaptureMode
            )
            dev_cfg = LogicDeviceConfiguration(
                enabled_digital_channels=[],
                digital_sample_rate=10_000_000,
                enabled_analog_channels=analog_channels,
                analog_sample_rate=sample_rate)
            cap_cfg = CaptureConfiguration(
                capture_mode=TimedCaptureMode(duration_seconds=duration_seconds))

            capture = controller.manager.start_capture(
                device_configuration=dev_cfg,
                capture_configuration=cap_cfg)
            capture.wait()

            if output_directory is None:
                import tempfile
                output_directory = tempfile.mkdtemp(prefix="saleae_")
            os.makedirs(output_directory, exist_ok=True)

            capture.export_raw_data_csv(
                directory=output_directory,
                analog_channels=analog_channels)

            results = {}
            for fname in os.listdir(output_directory):
                if not fname.endswith('.csv'):
                    continue
                fpath = os.path.join(output_directory, fname)
                voltages = []
                with open(fpath, 'r') as f:
                    reader = csv.reader(f)
                    next(reader, None)
                    for row in reader:
                        try:
                            voltages.append(float(row[1]))
                        except (IndexError, ValueError):
                            continue
                if voltages:
                    results[fname] = {
                        "samples": len(voltages),
                        "min_V": round(min(voltages), 6),
                        "max_V": round(max(voltages), 6),
                        "mean_V": round(statistics.mean(voltages), 6),
                        "stdev_V": round(statistics.stdev(voltages), 6) if len(voltages) > 1 else 0.0,
                        "peak_to_peak_V": round(max(voltages) - min(voltages), 6),
                    }

            sal_path = os.path.join(output_directory, "capture.sal")
            try:
                capture.save_capture(filepath=sal_path)
            except Exception:
                sal_path = None
            capture.close()

            return {
                "status": "success",
                "duration_s": duration_seconds,
                "sample_rate": sample_rate,
                "channels": analog_channels,
                "analysis": results,
                "csv_directory": output_directory,
                "capture_file": sal_path,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    # ── One-Shot Capture + Analyze Digital ──────────────────────

    @mcp.tool("capture_and_analyze_digital")
    def capture_and_analyze_digital(ctx: Context,
                                    digital_channels: List[int],
                                    duration_seconds: float,
                                    sample_rate: int = 10_000_000,
                                    digital_threshold_volts: Optional[float] = None,
                                    output_directory: Optional[str] = None) -> Dict[str, Any]:
        """One-shot: capture and analyze digital channels.
        Returns transition count, frequency estimate, duty cycle.

        Args:
            digital_channels: e.g. [0,1]
            duration_seconds: capture length in seconds
            sample_rate: digital sample rate (default 10 MHz)
            digital_threshold_volts: threshold (default None). Set to None for devices that don't support it (Logic 8).
            output_directory: where to save CSV (default: temp dir)
        """
        try:
            controller._ensure_manager()
            from saleae.automation import (
                LogicDeviceConfiguration, CaptureConfiguration, TimedCaptureMode
            )
            dev_cfg = LogicDeviceConfiguration(
                enabled_digital_channels=digital_channels,
                digital_sample_rate=sample_rate,
                enabled_analog_channels=[],
                digital_threshold_volts=digital_threshold_volts)
            cap_cfg = CaptureConfiguration(
                capture_mode=TimedCaptureMode(duration_seconds=duration_seconds))

            capture = controller.manager.start_capture(
                device_configuration=dev_cfg,
                capture_configuration=cap_cfg)
            capture.wait()

            if output_directory is None:
                import tempfile
                output_directory = tempfile.mkdtemp(prefix="saleae_")
            os.makedirs(output_directory, exist_ok=True)

            capture.export_raw_data_csv(
                directory=output_directory,
                digital_channels=digital_channels)

            results = {}
            for fname in os.listdir(output_directory):
                if not fname.endswith('.csv'):
                    continue
                fpath = os.path.join(output_directory, fname)
                transitions = 0
                times = []
                values = []
                with open(fpath, 'r') as f:
                    reader = csv.reader(f)
                    next(reader, None)
                    prev_val = None
                    for row in reader:
                        try:
                            t = float(row[0])
                            v = int(row[1])
                            times.append(t)
                            values.append(v)
                            if prev_val is not None and v != prev_val:
                                transitions += 1
                            prev_val = v
                        except (IndexError, ValueError):
                            continue
                info = {"samples": len(values), "transitions": transitions}
                if transitions >= 2 and len(times) >= 2:
                    total_time = times[-1] - times[0]
                    if total_time > 0:
                        info["estimated_freq_Hz"] = round(transitions / (2 * total_time), 2)
                if values:
                    high_count = sum(1 for v in values if v == 1)
                    info["duty_cycle_pct"] = round(100.0 * high_count / len(values), 2)
                results[fname] = info

            sal_path = os.path.join(output_directory, "capture.sal")
            try:
                capture.save_capture(filepath=sal_path)
            except Exception:
                sal_path = None
            capture.close()

            return {
                "status": "success",
                "duration_s": duration_seconds,
                "sample_rate": sample_rate,
                "channels": digital_channels,
                "analysis": results,
                "csv_directory": output_directory,
                "capture_file": sal_path,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Advanced Trigger & Protocol Tools ───────────────────────

    @mcp.tool("start_capture_with_trigger")
    def start_capture_with_trigger(ctx: Context,
                                   device_config_name: str,
                                   trigger_channel_index: int,
                                   trigger_type: str,
                                   after_trigger_seconds: float = 5.0,
                                   trim_data_seconds: Optional[float] = None,
                                   device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a capture that waits for a digital trigger.
        
        Args:
            device_config_name: Name of the device configuration
            trigger_channel_index: The digital channel index to trigger on
            trigger_type: 'RISING', 'FALLING', 'PULSE_HIGH', 'PULSE_LOW'
            after_trigger_seconds: How much data to capture after the trigger
            trim_data_seconds: Optional duration to keep (similar to regular capture duration). If None, keeps all data.
            after_trigger_seconds defines how long to record *after* the trigger event.
        """
        try:
            # Call controller method
            # Note: trim_data_seconds is optional in Logic 2 API
            res = controller.start_capture_with_trigger(
                device_config_name=device_config_name,
                trigger_channel_index=trigger_channel_index,
                trigger_type=trigger_type,
                after_trigger_seconds=after_trigger_seconds,
                trim_data_seconds=trim_data_seconds,
                device_id=device_id
            )
            return {"status": "success", "message": "Capture started with trigger", "details": res}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool("add_protocol_analyzer")
    def add_protocol_analyzer(ctx: Context,
                              name: str,
                              label: str,
                              settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a protocol analyzer (decoder) to the active capture.
        
        Args:
            name: The analyzer type name (e.g. 'Async Serial', 'I2C', 'SPI')
            label: A unique name for this analyzer instance
            settings: Dictionary of settings (e.g. {'Input Channel': 0, 'Bit Rate': 115200})
        """
        try:
            lbl = controller.add_analyzer(analyzer_name=name, label=label, settings=settings)
            return {"status": "success", "label": lbl}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool("export_analyzer_data")
    def export_analyzer_data(ctx: Context,
                             filepath: str,
                             analyzer_label: str) -> Dict[str, Any]:
        """
        Export decoded data from a protocol analyzer to CSV.
        
        Args:
            filepath: Destination file path
            analyzer_label: The label given when adding the analyzer
        """
        try:
            res = controller.export_analyzer_data(filepath=filepath, analyzer_label=analyzer_label)
            return {"status": "success", "filepath": res["filepath"]}
        except Exception as e:
            return {"status": "error", "message": str(e)}