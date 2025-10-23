from mcp import types
from mcp.server.fastmcp import FastMCP, Context
from typing import Optional, Dict, Any, List, Union
from saleae.automation import DeviceType
from saleae import Saleae
import os
import json
import time
import logging
import sys  # added for argv inspection
from logic_analyzer_mcp.mcp_tools_experimental import setup_mcp_tools_experimental

logger = logging.getLogger(__name__)

# Use shared saleae manager for instance creation/caching
from logic_analyzer_mcp.saleae_manager import get_saleae

def setup_mcp_tools(mcp: FastMCP, controller=None, enable_logic2: Optional[bool] = None) -> None:
    """Setup MCP tools for Saleae Logic control.

    If enable_logic2 is None, detection falls back to environment LOGIC2 or CLI args (--logic2).
    """
    # Determine whether to enable Logic2 experimental tools
    if enable_logic2 is None:
        env_val = os.environ.get("LOGIC2")
        if env_val and str(env_val).lower() in ("1", "true", "yes"):
            use_logic2 = True
        elif any(arg == "logic2" or arg.startswith("--logic2") for arg in sys.argv[1:]):
            use_logic2 = True
        else:
            use_logic2 = False
    else:
        use_logic2 = bool(enable_logic2)

    if use_logic2:
        try:
            setup_mcp_tools_experimental(mcp, controller)
            logger.info("Logic2 experimental MCP tools enabled (setup_mcp_tools_experimental called).")
        except Exception as e:
            logger.warning(f"setup_mcp_tools_experimental not available or failed: {e}")
    else:
        logger.info("Logic2 experimental MCP tools not enabled.")

    # Add python-saleae specific tools
    @mcp.tool("saleae_connect")
    def saleae_connect(ctx: Context) -> Dict[str, Any]:
        """Connect to Saleae Logic software using python-saleae."""
        try:
            from controllers.saleae_controller import SaleaeController
            controller = SaleaeController()
            if controller.connect():
                return {"status": "success", "message": "Connected to Saleae Logic"}
            return {"status": "error", "message": "Failed to connect to Saleae Logic"}
        except Exception as e:
            return {"status": "error", "message": f"Error connecting to Saleae Logic: {str(e)}"}

    @mcp.tool("saleae_configure")
    def saleae_configure(ctx: Context,
                        digital_channels: List[int],
                        digital_sample_rate: int,
                        analog_channels: Optional[List[int]] = None,
                        analog_sample_rate: Optional[int] = None,
                        trigger_channel: Optional[int] = None,
                        trigger_type: Optional[str] = None) -> Dict[str, Any]:
        """Configure Saleae Logic capture settings."""
        try:
            from controllers.saleae_controller import SaleaeController
            controller = SaleaeController()
            if controller.connect():
                if controller.configure_capture(
                    digital_channels=digital_channels,
                    digital_sample_rate=digital_sample_rate,
                    analog_channels=analog_channels,
                    analog_sample_rate=analog_sample_rate,
                    trigger_channel=trigger_channel,
                    trigger_type=trigger_type
                ):
                    return {"status": "success", "message": "Configured Saleae Logic capture"}
                return {"status": "error", "message": "Failed to configure capture"}
            return {"status": "error", "message": "Failed to connect to Saleae Logic"}
        except Exception as e:
            return {"status": "error", "message": f"Error configuring Saleae Logic: {str(e)}"}

    @mcp.tool("saleae_capture")
    def saleae_capture(ctx: Context,
                    duration_seconds: float,
                    output_file: str) -> Dict[str, Any]:
        """Start a capture with Saleae Logic and save to file."""
        try:
            from controllers.saleae_controller import SaleaeController
            controller = SaleaeController()
            if controller.connect():
                if controller.start_capture(duration_seconds):
                    # Wait for capture to complete
                    time.sleep(duration_seconds + 1)  # Add 1 second buffer
                    if controller.save_capture(output_file):
                        return {"status": "success", "message": f"Capture saved to {output_file}"}
                    return {"status": "error", "message": "Failed to save capture"}
                return {"status": "error", "message": "Failed to start capture"}
            return {"status": "error", "message": "Failed to connect to Saleae Logic"}
        except Exception as e:
            return {"status": "error", "message": f"Error during capture: {str(e)}"}

    @mcp.tool("saleae_export")
    def saleae_export(ctx: Context,
                    input_file: str,
                    output_file: str,
                    format: str = 'csv',
                    digital_channels: Optional[List[int]] = None,
                    analog_channels: Optional[List[int]] = None,
                    time_span: Optional[List[float]] = None) -> Dict[str, Any]:
        """Export capture data to specified format."""
        try:
            from controllers.saleae_controller import SaleaeController
            controller = SaleaeController()
            return controller.export_data(
                input_file=input_file,
                output_file=output_file,
                format=format,
                digital_channels=digital_channels,
                analog_channels=analog_channels,
                time_span=time_span
            )
        except Exception as e:
            return {"status": "error", "message": f"Error during export: {str(e)}"}

    @mcp.tool("saleae_device_info")
    def saleae_device_info(ctx: Context) -> Dict[str, Any]:
        """Get information about the connected Saleae Logic device."""
        try:
            from controllers.saleae_controller import SaleaeController
            controller = SaleaeController()
            if controller.connect():
                info = controller.get_device_info()
                if info:
                    return {"status": "success", "device_info": info}
                return {"status": "error", "message": "Failed to get device info"}
            return {"status": "error", "message": "Failed to connect to Saleae Logic"}
        except Exception as e:
            return {"status": "error", "message": f"Error getting device info: {str(e)}"}

    # Parser-related tools
    @mcp.tool("parse_capture_file")
    def parse_capture_file(ctx: Context, 
                          capture_file: Optional[str] = None,
                          data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Initialize parser with a capture file or direct data and return basic information.
        
        Args:
            capture_file: Path to the capture file (optional)
            data: Direct data dictionary with duration, digital_channels, and analog_channels (optional)
        """
        try:
            if data is not None:
                # Validate required fields
                required_fields = ['duration', 'digital_channels', 'analog_channels']
                if not all(field in data for field in required_fields):
                    return {"status": "error", "message": f"Missing required fields: {required_fields}"}
                return {
                    "status": "success",
                    "duration": data['duration'],
                    "digital_channels": data['digital_channels'],
                    "analog_channels": data['analog_channels']
                }
            elif capture_file is not None:
                if not os.path.exists(capture_file):
                    return {"status": "error", "message": f"Capture file not found: {capture_file}"}
                
                # Get Saleae instance
                saleae_instance = get_saleae()
                if saleae_instance is None:
                    # Try to launch Saleae software
                    try:
                        # First check if Saleae is installed in common locations
                        common_paths = [
                            os.path.expandvars(r"%ProgramFiles%\\Saleae\\Logic\\Logic.exe"),
                            os.path.expandvars(r"%ProgramFiles(x86)%\\Saleae\\Logic\\Logic.exe"),
                            os.path.expanduser("~\\AppData\\Local\\Programs\\Saleae\\Logic\\Logic.exe")
                        ]
                        
                        saleae_path = None
                        for path in common_paths:
                            if os.path.exists(path):
                                saleae_path = path
                                break
                        
                        if saleae_path is None:
                            # Fall back to offline mode
                            logger.warning("Saleae Logic software not found. Falling back to offline mode.")
                            return {
                                "status": "success",
                                # "message": "Running in offline mode",
                                "file_info": {
                                    "path": capture_file,
                                    "format": "Saleae Logic (.sal)",
                                    "size": os.path.getsize(capture_file),
                                    "modified": os.path.getmtime(capture_file)
                                }
                            }
                        
                        # Try to launch with the found path
                        saleae_instance = Saleae()
                        saleae_instance.launch()
                        # Wait a bit for the software to start
                        time.sleep(2)
                    except Exception as launch_error:
                        # Fall back to offline mode
                        logger.warning(f"Failed to launch Saleae software: {launch_error}. Falling back to offline mode.")
                        return {
                            "status": "success",
                            # "message": "Running in offline mode",
                            "file_info": {
                                "path": capture_file,
                                "format": "Saleae Logic (.sal)",
                                "size": os.path.getsize(capture_file),
                                "modified": os.path.getmtime(capture_file)
                            }
                        }
                
                try:
                    # Load the capture file using Saleae API
                    capture = saleae_instance.load_capture(capture_file)
                    
                    return {
                        "status": "success",
                        "file_info": {
                            "path": capture_file,
                            "format": "Saleae Logic (.sal)",
                            "duration": capture.duration,
                            "digital_channels": capture.digital_channels,
                            "analog_channels": capture.analog_channels,
                            "digital_sample_rate": capture.digital_sample_rate,
                            "analog_sample_rate": capture.analog_sample_rate
                        }
                    }
                except Exception as e:
                    # Fall back to offline mode
                    logger.warning(f"Failed to parse capture file with Saleae API: {e}. Falling back to offline mode.")
                    return {
                        "status": "success",
                        # "message": "Running in offline mode",
                        "file_info": {
                            "path": capture_file,
                            "format": "Saleae Logic (.sal)",
                            "size": os.path.getsize(capture_file),
                            "modified": os.path.getmtime(capture_file)
                        }
                    }
            else:
                return {"status": "error", "message": "Either capture_file or data must be provided"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to parse capture file: {str(e)}"}
        
    @mcp.tool("get_sample_rate")
    def get_sample_rate(ctx: Context,
                       capture_file: Optional[str] = None,
                       sample_rate: Optional[float] = None,
                       channel: int = 0) -> Dict[str, Any]:
        """
        Get the sample rate for a specific channel.
        
        Args:
            capture_file: Path to the capture file (optional)
            sample_rate: Direct sample rate value (optional)
            channel: Channel number
        """
        try:
            if sample_rate is not None:
                return {
                    "status": "success",
                    "sample_rate": sample_rate
                }
            elif capture_file is not None:
                if not os.path.exists(capture_file):
                    raise FileNotFoundError(f"Capture file not found: {capture_file}")
                saleae_instance = get_saleae()
                if saleae_instance is None:
                    return {"status": "error", "message": "Saleae instance not available"}
                rate = saleae_instance.get_sample_rate(capture_file, channel)
                return {
                    "status": "success",
                    "sample_rate": rate
                }
            else:
                return {"status": "error", "message": "Either capture_file or sample_rate must be provided"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get sample rate: {str(e)}"}


    @mcp.tool("get_digital_data_mcp")
    def get_digital_data_mcp(ctx: Context,
                        capture_file: str,
                        channel: int = 0,
                        start_time: Optional[float] = None,
                        end_time: Optional[float] = None,
                        max_samples: Optional[int] = None) -> Dict[str, Any]:
        """Get digital data from a capture file."""
        try:
            from controllers.saleae_controller import SaleaeController
            controller = SaleaeController()
            return controller.get_digital_data(
                capture_file=capture_file,
                channel=channel,
                start_time=start_time,
                end_time=end_time,
                max_samples=max_samples
            )
        except Exception as e:
            return {"status": "error", "message": f"Error getting digital data: {str(e)}"}
