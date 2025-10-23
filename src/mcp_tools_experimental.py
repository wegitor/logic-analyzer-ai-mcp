from mcp import types
from mcp.server.fastmcp import FastMCP, Context
from typing import Optional, Dict, Any, List, Union
from saleae.automation import DeviceType
from saleae import Saleae
import os
import json
import time
import logging

# Use shared saleae manager for instance creation/caching
from logic_analyzer_mcp.saleae_manager import get_saleae

logger = logging.getLogger(__name__)

# Try to import DeviceType if available
try:
    from saleae.automation import DeviceType
except Exception:
    DeviceType = None

def setup_mcp_tools_experimental(mcp: FastMCP, controller=None) -> None:

    controller_instance = controller

    # if controller is not None:
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
