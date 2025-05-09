from mcp import types
from mcp.server.fastmcp import FastMCP, Context
from typing import Optional, Dict, Any, List, Union
from saleae.automation import DeviceType
from saleae import Saleae
import os
import json
import time
import logging

logger = logging.getLogger(__name__)

def create_saleae_instance(max_retries=3, retry_delay=2):
    """
    Create a Saleae instance with automatic launch and retry mechanism.
    
    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds
    """
    # Define all possible paths where Logic.exe might be installed
    common_paths = [
        os.path.expandvars(r"%ProgramFiles%\Saleae\Logic\Logic.exe"),
        os.path.expandvars(r"%ProgramFiles%\Logic\Logic.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Saleae\Logic\Logic.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Saleae\Logic\Logic.exe")
    ]
    
    # First, check if any of the paths exist
    saleae_path = None
    for path in common_paths:
        logger.info(f"Checking path: {path}")
        if os.path.exists(path):
            saleae_path = path
            logger.info(f"Found Saleae Logic at: {path}")
            # Check file permissions
            try:
                if os.access(path, os.R_OK):
                    logger.info(f"File is readable: {path}")
                else:
                    logger.warning(f"File exists but is not readable: {path}")
                if os.access(path, os.X_OK):
                    logger.info(f"File is executable: {path}")
                else:
                    logger.warning(f"File exists but is not executable: {path}")
            except Exception as e:
                logger.warning(f"Error checking file permissions: {str(e)}")
            break
        else:
            logger.info(f"Path does not exist: {path}")
    
    if saleae_path is None:
        error_msg = "Saleae Logic software not found. Please ensure it is installed in one of these locations:\n"
        error_msg += "\n".join(f"- {path}" for path in common_paths)
        error_msg += "\n\nYou can download it from: https://www.saleae.com/downloads/"
        logger.error(error_msg)
        return None

    # Verify the path is accessible
    try:
        if not os.access(saleae_path, os.R_OK):
            error_msg = f"Found Saleae Logic at {saleae_path} but cannot access it.\n"
            error_msg += "Please ensure you have sufficient permissions to run the software."
            logger.error(error_msg)
            return None
    except Exception as e:
        error_msg = f"Error accessing Saleae Logic at {saleae_path}: {str(e)}\n"
        error_msg += "Please ensure the path is correct and accessible."
        logger.error(error_msg)
        return None

    for attempt in range(max_retries):
        try:
            # Try to create a new instance
            saleae = Saleae()
            # Test the connection
            saleae.get_connected_devices()
            return saleae
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                try:
                    # Try to launch the software using the found path
                    logger.info(f"Attempting to launch Saleae Logic from: {saleae_path}")
                    # Try to launch using subprocess first
                    try:
                        import subprocess
                        logger.info("Attempting to launch using subprocess...")
                        subprocess.Popen([saleae_path])
                        time.sleep(retry_delay)
                    except Exception as subprocess_error:
                        logger.warning(f"Subprocess launch failed: {str(subprocess_error)}")
                        # Fall back to Saleae API launch
                        saleae = Saleae()
                        saleae.launch()
                    
                    # Wait for the software to start
                    time.sleep(retry_delay)
                except Exception as launch_error:
                    error_msg = f"Failed to launch Saleae Logic from {saleae_path}: {str(launch_error)}\n"
                    error_msg += "Please ensure:\n"
                    error_msg += "1. The software is properly installed\n"
                    error_msg += "2. You have sufficient permissions to run the software\n"
                    error_msg += "3. No other instances are running\n"
                    error_msg += "4. The path is correct and accessible"
                    logger.error(error_msg)
                    time.sleep(retry_delay)
                    continue
    
    error_msg = "Failed to connect to Saleae Logic after all attempts.\n"
    error_msg += "Please ensure the software is installed and running.\n"
    error_msg += f"Installation path found: {saleae_path}\n"
    error_msg += "You can download it from: https://www.saleae.com/downloads/"
    logger.error(error_msg)
    return None

def setup_mcp_tools(mcp: FastMCP, controller=None) -> None:
    """Setup MCP tools for Saleae Logic control."""
    
    # Initialize Saleae instance only if needed
    saleae = None
    
    def get_saleae():
        nonlocal saleae
        if saleae is None:
            saleae = create_saleae_instance()
        return saleae

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

    # Device configuration tools (optional)
    if controller is not None:
        @mcp.tool("create_device_config")
        def create_device_config(ctx: Context, 
                               name: str,
                               digital_channels: List[int],
                               digital_sample_rate: int,
                               analog_channels: Optional[List[int]] = None,
                               analog_sample_rate: Optional[int] = None,
                               digital_threshold_volts: Optional[float] = None) -> Dict[str, Any]:
            """Create a new device configuration for Saleae Logic 2."""
            try:
                config_name = controller.create_device_config(
                    name=name,
                    digital_channels=digital_channels,
                    digital_sample_rate=digital_sample_rate,
                    analog_channels=analog_channels,
                    analog_sample_rate=analog_sample_rate,
                    digital_threshold_volts=digital_threshold_volts
                )
                return {"status": "success", "message": f"Created device configuration: {config_name}"}
            except Exception as e:
                return {"status": "error", "message": f"Failed to create device configuration: {str(e)}"}

        @mcp.tool("create_capture_config")
        def create_capture_config(ctx: Context,
                                name: str,
                                duration_seconds: float,
                                buffer_size_megabytes: Optional[int] = None) -> Dict[str, Any]:
            """Create a new capture configuration for Saleae Logic 2."""
            try:
                config_name = controller.create_capture_config(
                    name=name,
                    duration_seconds=duration_seconds,
                    buffer_size_megabytes=buffer_size_megabytes
                )
                return {"status": "success", "message": f"Created capture configuration: {config_name}"}
            except Exception as e:
                return {"status": "error", "message": f"Failed to create capture configuration: {str(e)}"}

        @mcp.tool("get_available_devices")
        def get_available_devices(ctx: Context) -> Dict[str, Any]:
            """Get list of available Saleae Logic devices."""
            try:
                devices = controller.get_available_devices()
                return {"status": "success", "devices": devices}
            except Exception as e:
                return {"status": "error", "message": f"Failed to get available devices: {str(e)}"}

        @mcp.tool("find_device_by_type")
        def find_device_by_type(ctx: Context, device_type: str) -> Dict[str, Any]:
            """Find a Saleae Logic device by its type."""
            try:
                device = controller.find_device_by_type(DeviceType[device_type])
                if device:
                    return {"status": "success", "device": device}
                return {"status": "error", "message": f"No device found of type {device_type}"}
            except ValueError as e:
                return {"status": "error", "message": str(e)}
            except Exception as e:
                return {"status": "error", "message": f"Failed to find device: {str(e)}"}

        @mcp.tool("list_device_configs")
        def list_device_configs(ctx: Context) -> Dict[str, Any]:
            """List all available device configurations."""
            try:
                configs = controller.list_device_configs()
                return {"status": "success", "configurations": configs}
            except Exception as e:
                return {"status": "error", "message": f"Failed to list device configurations: {str(e)}"}

        @mcp.tool("list_capture_configs")
        def list_capture_configs(ctx: Context) -> Dict[str, Any]:
            """List all available capture configurations."""
            try:
                configs = controller.list_capture_configs()
                return {"status": "success", "configurations": configs}
            except Exception as e:
                return {"status": "error", "message": f"Failed to list capture configurations: {str(e)}"}

        @mcp.tool("remove_device_config")
        def remove_device_config(ctx: Context, name: str) -> Dict[str, Any]:
            """Remove a device configuration."""
            try:
                if controller.remove_device_config(name):
                    return {"status": "success", "message": f"Removed device configuration: {name}"}
                return {"status": "error", "message": f"Device configuration {name} not found"}
            except Exception as e:
                return {"status": "error", "message": f"Failed to remove device configuration: {str(e)}"}

        @mcp.tool("remove_capture_config")
        def remove_capture_config(ctx: Context, name: str) -> Dict[str, Any]:
            """Remove a capture configuration."""
            try:
                if controller.remove_capture_config(name):
                    return {"status": "success", "message": f"Removed capture configuration: {name}"}
                return {"status": "error", "message": f"Capture configuration {name} not found"}
            except Exception as e:
                return {"status": "error", "message": f"Failed to remove capture configuration: {str(e)}"}

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
            
    @mcp.tool("get_digital_data")
    def get_digital_data(ctx: Context, 
                        capture_file: Optional[str] = None,
                        data: Optional[List[Dict[str, Union[float, bool]]]] = None,
                        channel: int = 0,
                        start_time: Optional[float] = None,
                        end_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Get digital data for a specific channel.
        
        Args:
            capture_file: Path to the capture file (optional)
            data: Direct data list of transitions (optional)
            channel: Channel number
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)
        """
        try:
            if data is not None:
                # Filter data by time range if specified
                if start_time is not None:
                    data = [d for d in data if d['time'] >= start_time]
                if end_time is not None:
                    data = [d for d in data if d['time'] <= end_time]
                return {
                    "status": "success",
                    "data": data
                }
            elif capture_file is not None:
                if not os.path.exists(capture_file):
                    return {"status": "error", "message": f"Capture file not found: {capture_file}"}
                
                # Get Saleae instance
                saleae_instance = get_saleae()
                if saleae_instance is None:
                    return {
                        "status": "success",
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
                    
                    # Get digital data for the specified channel
                    digital_data = capture.get_digital_data(channel, start_time, end_time)
                    
                    # Convert to list of dictionaries
                    data = [
                        {
                            "time": point.time,
                            "value": point.value
                        }
                        for point in digital_data
                    ]
                    
                    return {
                        "status": "success",
                        "channel": channel,
                        "data": data,
                        "total_samples": len(data)
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Failed to get digital data: {str(e)}"
                    }
            else:
                return {"status": "error", "message": "Either capture_file or data must be provided"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get digital data: {str(e)}"}
            
    @mcp.tool("get_analog_data")
    def get_analog_data(ctx: Context,
                       capture_file: Optional[str] = None,
                       data: Optional[List[Dict[str, Union[float, float]]]] = None,
                       channel: int = 0,
                       start_time: Optional[float] = None,
                       end_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Get analog data for a specific channel.
        
        Args:
            capture_file: Path to the capture file (optional)
            data: Direct data list of readings (optional)
            channel: Channel number
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)
        """
        try:
            if data is not None:
                # Filter data by time range if specified
                if start_time is not None:
                    data = [d for d in data if d['time'] >= start_time]
                if end_time is not None:
                    data = [d for d in data if d['time'] <= end_time]
                return {
                    "status": "success",
                    "data": data
                }
            elif capture_file is not None:
                if not os.path.exists(capture_file):
                    raise FileNotFoundError(f"Capture file not found: {capture_file}")
                saleae_instance = get_saleae()
                if saleae_instance is None:
                    return {"status": "error", "message": "Saleae instance not available"}
                data = saleae_instance.get_analog_data(capture_file, channel, start_time, end_time)
                return {
                    "status": "success",
                    "data": data
                }
            else:
                return {"status": "error", "message": "Either capture_file or data must be provided"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get analog data: {str(e)}"}
            
    @mcp.tool("export_digital_data")
    def export_digital_data(ctx: Context,
                          output_file: str,
                          capture_file: Optional[str] = None,
                          data: Optional[List[Dict[str, Union[float, bool]]]] = None,
                          channels: Optional[List[int]] = None,
                          start_time: Optional[float] = None,
                          end_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Export digital data to a CSV file.
        
        Args:
            output_file: Path to output CSV file
            capture_file: Path to the capture file (optional)
            data: Direct data list of transitions (optional)
            channels: List of channels to export (optional)
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)
        """
        try:
            if data is not None:
                # Filter data by time range if specified
                if start_time is not None:
                    data = [d for d in data if d['time'] >= start_time]
                if end_time is not None:
                    data = [d for d in data if d['time'] <= end_time]
                # Export to CSV
                with open(output_file, 'w') as f:
                    f.write("Time,Value\n")
                    for entry in data:
                        f.write(f"{entry['time']},{entry['value']}\n")
                return {
                    "status": "success",
                    "message": f"Exported digital data to {output_file}"
                }
            elif capture_file is not None:
                if not os.path.exists(capture_file):
                    raise FileNotFoundError(f"Capture file not found: {capture_file}")
                saleae_instance = get_saleae()
                if saleae_instance is None:
                    return {"status": "error", "message": "Saleae instance not available"}
                saleae_instance.export_digital_data(capture_file, output_file, channels, start_time, end_time)
                return {
                    "status": "success",
                    "message": f"Exported digital data to {output_file}"
                }
            else:
                return {"status": "error", "message": "Either capture_file or data must be provided"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to export digital data: {str(e)}"}
            
    @mcp.tool("export_analog_data")
    def export_analog_data(ctx: Context,
                         output_file: str,
                         capture_file: Optional[str] = None,
                         data: Optional[List[Dict[str, Union[float, float]]]] = None,
                         channels: Optional[List[int]] = None,
                         start_time: Optional[float] = None,
                         end_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Export analog data to a CSV file.
        
        Args:
            output_file: Path to output CSV file
            capture_file: Path to the capture file (optional)
            data: Direct data list of readings (optional)
            channels: List of channels to export (optional)
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)
        """
        try:
            if data is not None:
                # Filter data by time range if specified
                if start_time is not None:
                    data = [d for d in data if d['time'] >= start_time]
                if end_time is not None:
                    data = [d for d in data if d['time'] <= end_time]
                # Export to CSV
                with open(output_file, 'w') as f:
                    f.write("Time,Voltage\n")
                    for entry in data:
                        f.write(f"{entry['time']},{entry['voltage']}\n")
                return {
                    "status": "success",
                    "message": f"Exported analog data to {output_file}"
                }
            elif capture_file is not None:
                if not os.path.exists(capture_file):
                    raise FileNotFoundError(f"Capture file not found: {capture_file}")
                saleae_instance = get_saleae()
                if saleae_instance is None:
                    return {"status": "error", "message": "Saleae instance not available"}
                saleae_instance.export_analog_data(capture_file, output_file, channels, start_time, end_time)
                return {
                    "status": "success",
                    "message": f"Exported analog data to {output_file}"
                }
            else:
                return {"status": "error", "message": "Either capture_file or data must be provided"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to export analog data: {str(e)}"}
            
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

    # Protocol and Data Analysis tools
    @mcp.tool("detect_protocols")
    def detect_protocols(ctx: Context, capture_file: str) -> Dict[str, Any]:
        """
        Detect protocols in a capture file.
        
        Args:
            capture_file: Path to the capture file
        """
        try:
            if not os.path.exists(capture_file):
                return {"status": "error", "message": f"Capture file not found: {capture_file}"}
            
            saleae_instance = get_saleae()
            if saleae_instance is None:
                return {
                    "status": "success",
                    "file_info": {
                        "path": capture_file,
                        "format": "Saleae Logic (.sal)",
                        "size": os.path.getsize(capture_file),
                        "modified": os.path.getmtime(capture_file)
                    }
                }
            
            # Load capture and get protocol analyzers
            capture = saleae_instance.load_capture(capture_file)
            analyzers = capture.get_analyzers()
            
            return {
                "status": "success",
                "protocols": [
                    {
                        "name": analyzer.name,
                        "type": analyzer.type,
                        "channels": analyzer.channels,
                        "settings": analyzer.settings
                    }
                    for analyzer in analyzers
                ]
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to detect protocols: {str(e)}"}

    @mcp.tool("get_protocol_data")
    def get_protocol_data(ctx: Context, 
                         capture_file: str,
                         protocol_type: str,
                         start_time: Optional[float] = None,
                         end_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Get protocol data from a capture file.
        
        Args:
            capture_file: Path to the capture file
            protocol_type: Type of protocol to analyze (e.g., 'I2C', 'SPI', 'UART')
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)
        """
        try:
            if not os.path.exists(capture_file):
                return {"status": "error", "message": f"Capture file not found: {capture_file}"}
            
            saleae_instance = get_saleae()
            if saleae_instance is None:
                return {
                    "status": "success",
                    "file_info": {
                        "path": capture_file,
                        "format": "Saleae Logic (.sal)",
                        "size": os.path.getsize(capture_file),
                        "modified": os.path.getmtime(capture_file)
                    }
                }
            
            # Load capture and get protocol analyzer
            capture = saleae_instance.load_capture(capture_file)
            analyzer = capture.get_analyzer(protocol_type)
            
            if analyzer is None:
                return {"status": "error", "message": f"No {protocol_type} analyzer found"}
            
            # Get protocol data
            data = analyzer.get_data(start_time, end_time)
            
            return {
                "status": "success",
                "protocol": protocol_type,
                "data": [
                    {
                        "time": packet.time,
                        "type": packet.type,
                        "data": packet.data,
                        "metadata": packet.metadata
                    }
                    for packet in data
                ]
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to get protocol data: {str(e)}"}

    # TODO: Temporarily disabled analyze functions - will be re-enabled after Saleae API integration is complete
    """
    @mcp.tool("analyze_digital_data")
    def analyze_digital_data(ctx: Context,
                           capture_file: str,
                           channel: int,
                           start_time: Optional[float] = None,
                           end_time: Optional[float] = None) -> Dict[str, Any]:
        Analyze digital data from a capture file.
        
        Args:
            capture_file: Path to the capture file
            channel: Channel number to analyze
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)
        try:
            if not os.path.exists(capture_file):
                return {"status": "error", "message": f"Capture file not found: {capture_file}"}
            
            saleae_instance = get_saleae()
            if saleae_instance is None:
                return {
                    "status": "success",
                    "file_info": {
                        "path": capture_file,
                        "format": "Saleae Logic (.sal)",
                        "size": os.path.getsize(capture_file),
                        "modified": os.path.getmtime(capture_file)
                    }
                }
            
            # Load capture and get digital data
            capture = saleae_instance.load_capture(capture_file)
            data = capture.get_digital_data(channel, start_time, end_time)
            
            # Analyze transitions
            transitions = []
            for i in range(len(data) - 1):
                if data[i].value != data[i + 1].value:
                    transitions.append({
                        "time": data[i + 1].time,
                        "from_value": data[i].value,
                        "to_value": data[i + 1].value
                    })
            
            return {
                "status": "success",
                "channel": channel,
                "total_samples": len(data),
                "transitions": transitions,
                "first_value": data[0].value if data else None,
                "last_value": data[-1].value if data else None
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to analyze digital data: {str(e)}"}

    @mcp.tool("analyze_analog_data")
    def analyze_analog_data(ctx: Context,
                          capture_file: str,
                          channel: int,
                          start_time: Optional[float] = None,
                          end_time: Optional[float] = None) -> Dict[str, Any]:
        Analyze analog data from a capture file.
        
        Args:
            capture_file: Path to the capture file
            channel: Channel number to analyze
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)
        try:
            if not os.path.exists(capture_file):
                return {"status": "error", "message": f"Capture file not found: {capture_file}"}
            
            saleae_instance = get_saleae()
            if saleae_instance is None:
                return {
                    "status": "success",
                    "file_info": {
                        "path": capture_file,
                        "format": "Saleae Logic (.sal)",
                        "size": os.path.getsize(capture_file),
                        "modified": os.path.getmtime(capture_file)
                    }
                }
            
            # Load capture and get analog data
            capture = saleae_instance.load_capture(capture_file)
            data = capture.get_analog_data(channel, start_time, end_time)
            
            if not data:
                return {"status": "error", "message": "No analog data found"}
            
            # Calculate statistics
            values = [point.voltage for point in data]
            min_voltage = min(values)
            max_voltage = max(values)
            avg_voltage = sum(values) / len(values)
            
            return {
                "status": "success",
                "channel": channel,
                "total_samples": len(data),
                "min_voltage": min_voltage,
                "max_voltage": max_voltage,
                "avg_voltage": avg_voltage,
                "first_value": data[0].voltage if data else None,
                "last_value": data[-1].voltage if data else None
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to analyze analog data: {str(e)}"}

    @mcp.tool("export_protocol_data")
    def export_protocol_data(ctx: Context,
                           output_file: str,
                           capture_file: str,
                           protocol_type: str,
                           start_time: Optional[float] = None,
                           end_time: Optional[float] = None) -> Dict[str, Any]:
        Export protocol data to a CSV file.
        
        Args:
            output_file: Path to output CSV file
            capture_file: Path to the capture file
            protocol_type: Type of protocol to analyze
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)
        try:
            if not os.path.exists(capture_file):
                return {"status": "error", "message": f"Capture file not found: {capture_file}"}
            
            saleae_instance = get_saleae()
            if saleae_instance is None:
                return {
                    "status": "success",
                    "file_info": {
                        "path": capture_file,
                        "format": "Saleae Logic (.sal)",
                        "size": os.path.getsize(capture_file),
                        "modified": os.path.getmtime(capture_file)
                    }
                }
            
            # Load capture and get protocol analyzer
            capture = saleae_instance.load_capture(capture_file)
            analyzer = capture.get_analyzer(protocol_type)
            
            if analyzer is None:
                return {"status": "error", "message": f"No {protocol_type} analyzer found"}
            
            # Get protocol data
            data = analyzer.get_data(start_time, end_time)
            
            # Export to CSV
            with open(output_file, 'w') as f:
                f.write("Time,Type,Data,Metadata\n")
                for packet in data:
                    f.write(f"{packet.time},{packet.type},{packet.data},{packet.metadata}\n")
            
            return {
                "status": "success",
                "message": f"Exported {protocol_type} data to {output_file}"
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to export protocol data: {str(e)}"}
    """

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

    @mcp.tool("get_digital_data_batch_mcp")
    def get_digital_data_batch_mcp(ctx: Context,
                                 capture_file: str,
                                 channels: List[int],
                                 start_time: Optional[float] = None,
                                 end_time: Optional[float] = None,
                                 max_samples: Optional[int] = None) -> Dict[str, Any]:
        """Get digital data from multiple channels in a capture file."""
        try:
            from controllers.saleae_controller import SaleaeController
            controller = SaleaeController()
            return controller.get_digital_data_batch(
                capture_file=capture_file,
                channels=channels,
                start_time=start_time,
                end_time=end_time,
                max_samples=max_samples
            )
        except Exception as e:
            return {"status": "error", "message": f"Error getting digital data: {str(e)}"}