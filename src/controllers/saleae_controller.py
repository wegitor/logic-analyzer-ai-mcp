from typing import Optional, List, Dict, Any, Union
import os
import time
import logging
from saleae import Saleae, Trigger, PerformanceOption
import psutil
import subprocess
# import pyautogui

logger = logging.getLogger(__name__)

class SaleaeController:
    def __init__(self):
        """Initialize the Saleae controller."""
        self.saleae = None
        self.connected_device = None
        self.sample_rate = None
        self.active_channels = None
        
        # Try to connect
        if not self.connect():
            logger.error("Failed to initialize Saleae connection")
            # Don't raise exception here, let the caller handle it

    def _find_saleae_software(self) -> Optional[str]:
        """Find Saleae Logic software installation path."""
        # Common installation paths for Windows
        possible_paths = [
            # Logic 1 paths (older version)
            os.path.expandvars(r"%ProgramFiles%\Saleae\Logic\Logic.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Saleae\Logic\Logic.exe"),
            os.path.expanduser(r"~\AppData\Local\Programs\Saleae\Logic\Logic.exe"),
            # Legacy paths
            os.path.expandvars(r"%ProgramFiles%\Logic\Logic.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Logic\Logic.exe")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found Saleae Logic software at: {path}")
                # Check permissions
                try:
                    if os.access(path, os.R_OK):
                        logger.info(f"  ✓ File is readable")
                    else:
                        logger.warning(f"  ✗ File is not readable")
                    if os.access(path, os.X_OK):
                        logger.info(f"  ✓ File is executable")
                    else:
                        logger.warning(f"  ✗ File is not executable")
                    return path
                except Exception as e:
                    logger.error(f"  ✗ Error checking permissions: {str(e)}")
                    
        logger.error("Saleae Logic software not found in common installation paths")
        return None

    def _launch_saleae_software(self) -> bool:
        """Launch Saleae Logic software if not running."""
        try:
            saleae_path = self._find_saleae_software()
            if not saleae_path:
                return False
                
            # Check if process is already running
            for proc in psutil.process_iter(['name']):
                if 'Logic.exe' in proc.info['name']:
                    logger.info("Saleae Logic software is already running")
                    return True
                    
            # Launch the software with elevated privileges
            logger.info(f"Launching Saleae Logic from: {saleae_path}")
            if os.name == 'nt':  # Windows
                try:
                    process = subprocess.Popen(
                        [saleae_path],
                        shell=True,
                        creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                except Exception as e:
                    logger.error(f"Failed to launch with elevated privileges: {str(e)}")
                    # Try without elevated privileges
                    process = subprocess.Popen([saleae_path])
            else:
                process = subprocess.Popen([saleae_path])
                
            # Wait for initial startup
            time.sleep(5)
            
            # Verify process is running
            if process.poll() is None:
                logger.info("Saleae Logic process is running")
                # Wait for Logic to initialize
                time.sleep(10)  # Give more time for Logic to fully initialize
                return True
            else:
                logger.error("Saleae Logic process exited immediately")
                return False
                
        except Exception as e:
            logger.error(f"Failed to launch Saleae Logic software: {str(e)}")
            return False

    def connect(self) -> bool:
        """
        Connect to Saleae Logic software.
        If connection fails, it attempts to launch the software and retry connection.
        """
        try:
            # First attempt to connect to an already running instance
            self.saleae = Saleae()
            logger.info("Successfully connected to an existing Saleae Logic instance.")
            self.connected_device = self.saleae.get_active_device()
            return True
        except Exception:
            logger.info("Could not connect to existing Saleae Logic instance. Attempting to launch...")
            
            # If connection fails, try launching the software
            if self._launch_saleae_software():
                logger.info("Saleae Logic software launched. Retrying connection...")
                # Retry connection after launching
                try:
                    # Give it a moment to initialize the server socket
                    time.sleep(2) 
                    self.saleae = Saleae()
                    logger.info("Successfully connected to Saleae Logic after launching.")
                    self.connected_device = self.saleae.get_active_device()
                    return True
                except Exception as e:
                    logger.error(f"Failed to connect to Saleae Logic after launching: {str(e)}")
                    return False
            else:
                logger.error("Failed to launch Saleae Logic software.")
                return False

    def configure_capture(self, 
                         digital_channels: List[int],
                         digital_sample_rate: int,
                         analog_channels: Optional[List[int]] = None,
                         analog_sample_rate: Optional[int] = None,
                         trigger_channel: Optional[int] = None,
                         trigger_type: Optional[str] = None) -> bool:
        """Configure capture settings."""
        try:
            # Set active channels
            if self.connected_device.type not in ['LOGIC_4_DEVICE', 'LOGIC_DEVICE']:
                self.saleae.set_active_channels(digital_channels, analog_channels)
            
            # Set sample rate
            if analog_channels and analog_sample_rate:
                self.saleae.set_sample_rate_by_minimum(digital_sample_rate, analog_sample_rate)
            else:
                self.saleae.set_sample_rate_by_minimum(digital_sample_rate, 0)
            
            # Set trigger if specified
            if trigger_channel is not None and trigger_type is not None:
                trigger_map = {
                    'high': Trigger.High,
                    'low': Trigger.Low,
                    'posedge': Trigger.Posedge,
                    'negedge': Trigger.Negedge,
                    'pospulse': Trigger.Pospulse,
                    'negpulse': Trigger.Negpulse
                }
                if trigger_type.lower() in trigger_map:
                    self.saleae.set_trigger_one_channel(trigger_channel, trigger_map[trigger_type.lower()])
            
            # Store current configuration
            self.active_channels = (digital_channels, analog_channels or [])
            self.sample_rate = self.saleae.get_sample_rate()
            
            return True
        except Exception as e:
            logger.error(f"Failed to configure capture: {str(e)}")
            return False

    def parse_capture(self, file_path: str) -> Dict[str, Any]:
        """Parse a capture file and return its contents."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"Capture file not found: {file_path}")
                return {"status": "error", "message": "File not found"}

            # Check file extension
            _, ext = os.path.splitext(file_path)
            if ext.lower() == '.logicdata':
                logger.info(f"Found Logic 1.x capture file: {file_path}")
                # For Logic 1.x, we can't parse the file programmatically
                # Return basic file info
                return {
                    "status": "success",
                    "message": "File exists, please open in Logic software",
                    "file_type": "logicdata",
                    "file_path": file_path,
                    "file_size": os.path.getsize(file_path),
                    "created": time.ctime(os.path.getctime(file_path)),
                    "modified": time.ctime(os.path.getmtime(file_path))
                }
            else:
                logger.error(f"Unsupported file format: {ext}")
                return {
                    "status": "error",
                    "message": f"Unsupported file format: {ext}",
                    "file_path": file_path
                }

        except Exception as e:
            logger.error(f"Failed to parse capture: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "file_path": file_path
            }

    def load_capture(self, file_path: str) -> bool:
        """Load a capture file."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"Capture file not found: {file_path}")
                return False
                
            # Check file extension
            _, ext = os.path.splitext(file_path)
            if ext.lower() == '.logicdata':
                logger.info(f"Found Logic 1.x capture file: {file_path}")
                logger.info("Please open the file manually in Saleae Logic software")
                return True
            else:
                logger.error(f"Unsupported file format: {ext}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load capture: {str(e)}")
            return False

    def start_capture(self, duration_seconds: float) -> bool:
        """Start a capture for specified duration."""
        try:
            # Verify connection is still active
            if not hasattr(self, 'saleae') or self.saleae is None:
                logger.error("Saleae connection not initialized")
                return False
                
            # Create a unique filename with timestamp
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            capture_file = os.path.join(os.getcwd(), f"capture_{timestamp}.logicdata")
            
            # Set capture duration
            logger.info(f"Setting capture duration to {duration_seconds} seconds...")
            self.saleae.set_capture_seconds(duration_seconds)
            
            # Start capture to file
            logger.info(f"Starting capture, saving to {capture_file}...")
            self.saleae.capture_to_file(capture_file)
            
            # Wait for processing to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)
                
            logger.info("Capture completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start capture: {str(e)}")
            logger.error("Please ensure Saleae Logic software is running")
            return False

    def stop_capture(self) -> bool:
        """Stop the current capture."""
        try:
            return self.saleae.capture_stop()
        except Exception as e:
            logger.error(f"Failed to stop capture: {str(e)}")
            return False

    def save_capture(self, file_path: str) -> bool:
        """Save the current capture to file."""
        try:
            self.saleae.save_to_file(file_path)
            return True
        except Exception as e:
            logger.error(f"Failed to save capture: {str(e)}")
            return False

    def _convert_sal_to_logicdata(self, sal_file: str, logicdata_file: str) -> bool:
        """Convert .sal file to .logicdata format using Saleae API."""
        try:
            # Ensure paths are absolute and use forward slashes
            sal_file = os.path.abspath(sal_file).replace('\\', '/')
            logicdata_file = os.path.abspath(logicdata_file).replace('\\', '/')
            
            # Ensure output directory exists
            output_dir = os.path.dirname(logicdata_file)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            logger.info(f"Converting {sal_file} to {logicdata_file}")
            
            # Close any open files first
            try:
                self.saleae.close_all_tabs()
                time.sleep(1)  # Give it a moment to close
                logger.info("Closed all open tabs")
            except Exception as e:
                logger.warning(f"Failed to close tabs: {e}")
            
            # Open the .sal file
            try:
                logger.info("Attempting to load .sal file...")
                self.saleae.load_from_file(sal_file)
                logger.info("File load command sent")
            except Exception as e:
                logger.error(f"Failed to load .sal file: {e}")
                raise RuntimeError(f"Failed to load .sal file: {e}")
            
            # Wait for loading with timeout
            load_timeout = 30  # seconds
            start_time = time.time()
            try:
                while not self.saleae.is_processing_complete():
                    if time.time() - start_time > load_timeout:
                        raise TimeoutError("Loading .sal file timed out")
                    time.sleep(0.1)
                logger.info("File loading completed")
            except Exception as e:
                logger.error(f"Error while waiting for file to load: {e}")
                raise RuntimeError(f"Error while waiting for file to load: {e}")
            
            # Get active channels
            try:
                active_channels = self.saleae.get_active_channels()
                logger.info(f"Active channels: {active_channels}")
                if not active_channels or (not active_channels[0] and not active_channels[1]):
                    raise ValueError("No active channels found in the file")
            except Exception as e:
                logger.error(f"Failed to get active channels: {e}")
                raise RuntimeError(f"Failed to get active channels: {e}")
            
            # Export to .logicdata format
            try:
                logger.info("Starting export to .logicdata format...")
                self.saleae.export_data2(
                    logicdata_file,
                    digital_channels=active_channels[0],
                    analog_channels=active_channels[1],
                    format='logicdata'
                )
                logger.info("Export command sent")
            except Exception as e:
                logger.error(f"Failed to start export: {e}")
                raise RuntimeError(f"Failed to start export: {e}")
            
            # Wait for export with timeout
            export_timeout = 30  # seconds
            start_time = time.time()
            try:
                while not self.saleae.is_processing_complete():
                    if time.time() - start_time > export_timeout:
                        raise TimeoutError("Export to .logicdata timed out")
                    time.sleep(0.1)
                logger.info("Export completed")
            except Exception as e:
                logger.error(f"Error while waiting for export to complete: {e}")
                raise RuntimeError(f"Error while waiting for export to complete: {e}")
            
            # Verify the converted file exists
            if not os.path.exists(logicdata_file):
                raise FileNotFoundError(f"Converted .logicdata file not created: {logicdata_file}")
            
            # Verify file size
            file_size = os.path.getsize(logicdata_file)
            if file_size == 0:
                raise ValueError(f"Converted file is empty: {logicdata_file}")
            
            logger.info(f"Successfully converted .sal file to .logicdata format (size: {file_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to convert .sal file: {e}")
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Full error details:\n{error_details}")
            return False

    def export_data(self, 
                   input_file: str,
                   output_file: str,
                   format: str = 'csv',
                   digital_channels: Optional[List[int]] = None,
                   analog_channels: Optional[List[int]] = None,
                   time_span: Optional[List[float]] = None) -> Dict[str, Any]:
        """Export capture data to specified format."""
        try:
            # Verify input file exists
            if not os.path.exists(input_file):
                logger.error(f"Input file not found: {input_file}")
                return {
                    "status": "error",
                    "message": "Input file not found",
                    "details": f"File does not exist: {input_file}"
                }

            # Prepare paths
            input_file = os.path.abspath(input_file).replace('\\', '/')
            output_file = os.path.abspath(output_file).replace('\\', '/')

            # Ensure we're connected to Logic
            if not self.connect():
                return {
                    "status": "error",
                    "message": "Failed to connect to Logic",
                    "details": "Please make sure Logic software is running and try again"
                }

            # Handle .sal files by first exporting to .logicdata
            if input_file.lower().endswith('.sal'):
                logger.info(f"Converting .sal file to .logicdata format")
                temp_logicdata = os.path.splitext(input_file)[0] + '.logicdata'
                try:
                    # Check if file is accessible
                    if not os.access(input_file, os.R_OK):
                        raise PermissionError(f"No read permission for file: {input_file}")
                    
                    # Check file size
                    file_size = os.path.getsize(input_file)
                    if file_size == 0:
                        raise ValueError(f"File is empty: {input_file}")
                    
                    logger.info(f"File size: {file_size} bytes")
                    
                    # Try to convert .sal to .logicdata using API
                    if not self._convert_sal_to_logicdata(input_file, temp_logicdata):
                        return {
                            "status": "error",
                            "message": "Failed to convert .sal file",
                            "details": "Failed to convert .sal file using Saleae API. Please make sure the file is a valid .sal file."
                        }
                    
                    # Use the converted file
                    input_file = temp_logicdata
                    logger.info(f"Successfully converted to .logicdata format")
                    
                except PermissionError as e:
                    logger.error(f"Permission error: {e}")
                    return {
                        "status": "error",
                        "message": "Permission denied",
                        "details": str(e)
                    }
                except ValueError as e:
                    logger.error(f"Invalid file: {e}")
                    return {
                        "status": "error",
                        "message": "Invalid file",
                        "details": str(e)
                    }
                except TimeoutError as e:
                    logger.error(f"Operation timeout: {e}")
                    return {
                        "status": "error",
                        "message": "Operation timeout",
                        "details": str(e)
                    }
                except FileNotFoundError as e:
                    logger.error(f"File not found: {e}")
                    return {
                        "status": "error",
                        "message": "File not found",
                        "details": str(e)
                    }
                except Exception as e:
                    logger.error(f"Failed to convert .sal file: {str(e)}")
                    import traceback
                    error_details = traceback.format_exc()
                    logger.error(f"Full error details:\n{error_details}")
                    return {
                        "status": "error",
                        "message": "Failed to convert .sal file",
                        "details": f"Error during conversion: {str(e)}\n{error_details}"
                    }

            # Ensure output directory exists
            output_dir = os.path.dirname(output_file)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"Created output directory: {output_dir}")

            # Load the file
            logger.info(f"Loading capture file: {input_file}")
            self.saleae.load_from_file(input_file)
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)

            # Get channels if not provided
            if digital_channels is None or analog_channels is None:
                active_channels = self.saleae.get_active_channels()
                digital_channels = digital_channels or active_channels[0]
                analog_channels = analog_channels or active_channels[1]

            # Export data
            logger.info(f"Exporting data to: {output_file}")
            try:
                self.saleae.export_data2(
                    output_file,
                    digital_channels=digital_channels,
                    analog_channels=analog_channels,
                    time_span=time_span,
                    format=format
                )
                # Wait for export to complete
                export_timeout = 30  # seconds
                start_time = time.time()
                while not self.saleae.is_processing_complete():
                    if time.time() - start_time > export_timeout:
                        raise TimeoutError("Export operation timed out")
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Export failed: {e}")
                return {
                    "status": "error",
                    "message": "Failed to export data",
                    "details": str(e)
                }

            # Check if the output file exists
            if os.path.exists(output_file):
                logger.info(f"Successfully exported data to {output_file}")
                return {
                    "status": "success",
                    "message": f"Data exported to {output_file}",
                    "format": format,
                    "channels": {
                        "digital": digital_channels,
                        "analog": analog_channels
                    }
                }
            else:
                logger.error("Export file not created")
                return {
                    "status": "error",
                    "message": "Failed to export data",
                    "details": "Export file not created"
                }
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return {
                "status": "error",
                "message": "Failed to export data",
                "details": str(e)
            }

    def get_device_info(self) -> Dict[str, Any]:
        """Get information about the connected device."""
        try:
            device = self.saleae.get_active_device()
            digital_channels, analog_channels = self.saleae.get_active_channels()
            sample_rate = self.saleae.get_sample_rate()
            
            return {
                "device_type": device.type,
                "device_name": device.name,
                "device_id": device.id,
                "active_digital_channels": digital_channels,
                "active_analog_channels": analog_channels,
                "sample_rate": sample_rate
            }
        except Exception as e:
            logger.error(f"Failed to get device info: {str(e)}")
            return {}

    def close(self):
        """Close the connection to Saleae Logic."""
        try:
            if self.saleae:
                self.saleae.exit()
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}") 

    def get_digital_data(self,
                        capture_file: str,
                        channel: int = 0,
                        start_time: Optional[float] = None,
                        end_time: Optional[float] = None,
                        max_samples: Optional[int] = None) -> Dict[str, Any]:
        """Get digital data from a capture file."""
        try:
            # Load the capture file
            logger.info(f"Loading capture file: {capture_file}")
            self.saleae.load_from_file(capture_file)
            
            # Wait for processing to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)

            # Convert time span if provided
            time_span = None
            if start_time is not None and end_time is not None:
                time_span = [start_time, end_time]

            # Create a temporary CSV file
            temp_csv = os.path.splitext(capture_file)[0] + "_temp.csv"
            
            # Export digital data to CSV
            logger.info("Exporting digital data to CSV...")
            self.saleae.export_data2(
                temp_csv,
                digital_channels=[channel],
                time_span=time_span,
                format='csv'
            )
            
            # Wait for export to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)
            
            # Read and parse the exported data
            digital_data = []
            with open(temp_csv, 'r') as f:
                # Skip header
                next(f)
                for line in f:
                    timestamp, value = line.strip().split(',')
                    digital_data.append({
                        'time': float(timestamp),
                        'value': int(value)
                    })
            
            # Clean up temp file
            os.remove(temp_csv)
            
            # Apply max_samples if specified
            if max_samples is not None and len(digital_data) > max_samples:
                step = len(digital_data) // max_samples
                digital_data = digital_data[::step]
            
            logger.info("Successfully got digital data")
            return {
                "status": "success",
                "message": "Successfully got digital data",
                "data": digital_data
            }

        except Exception as e:
            logger.error(f"Failed to get digital data: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to get digital data: {str(e)}"
            }

    def get_digital_data_batch(self,
                             capture_file: str,
                             channels: List[int],
                             start_time: Optional[float] = None,
                             end_time: Optional[float] = None,
                             max_samples: Optional[int] = None) -> Dict[str, Any]:
        """Get digital data from multiple channels in a capture file."""
        try:
            # Load the capture file
            logger.info(f"Loading capture file: {capture_file}")
            self.saleae.load_from_file(capture_file)
            
            # Wait for processing to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)

            # Convert time span if provided
            time_span = None
            if start_time is not None and end_time is not None:
                time_span = [start_time, end_time]

            # Create a temporary CSV file
            temp_csv = os.path.splitext(capture_file)[0] + "_temp.csv"
            
            # Export digital data to CSV
            logger.info("Exporting digital data to CSV...")
            self.saleae.export_data2(
                temp_csv,
                digital_channels=channels,
                time_span=time_span,
                format='csv'
            )
            
            # Wait for export to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)
            
            # Read and parse the exported data
            channel_data = {}
            with open(temp_csv, 'r') as f:
                # Skip header
                next(f)
                for line in f:
                    timestamp, *values = line.strip().split(',')
                    for i, value in enumerate(values):
                        channel = channels[i]
                        if channel not in channel_data:
                            channel_data[channel] = []
                        channel_data[channel].append({
                            'time': float(timestamp),
                            'value': int(value)
                        })
            
            # Clean up temp file
            os.remove(temp_csv)
            
            # Apply max_samples if specified
            if max_samples is not None:
                for channel in channel_data:
                    if len(channel_data[channel]) > max_samples:
                        step = len(channel_data[channel]) // max_samples
                        channel_data[channel] = channel_data[channel][::step]
            
            logger.info("Successfully got digital data for all channels")
            return {
                "status": "success",
                "message": "Successfully got digital data for all channels",
                "channels": channel_data
            }

        except Exception as e:
            logger.error(f"Failed to get digital data: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to get digital data: {str(e)}"
            }

    def detect_protocols(self, file_path: str) -> Dict[str, Any]:
        """Detect protocols in a capture file."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"Capture file not found: {file_path}")
                return {"status": "error", "message": "File not found"}

            # Check file extension
            _, ext = os.path.splitext(file_path)
            if ext.lower() == '.logicdata':
                logger.info(f"Found Logic 1.x capture file: {file_path}")
                
                try:
                    # First, try to open the file in Logic
                    logger.info("Opening capture file in Logic...")
                    try:
                        # Try to open the file using the Saleae API
                        self.saleae.open_capture_file(file_path)
                        logger.info("Successfully opened capture file")
                    except Exception as e:
                        logger.warning(f"Could not open file via API: {str(e)}")
                        logger.info("Please open the file manually in Logic software")
                        return {
                            "status": "error",
                            "message": "Please open the file manually in Logic software",
                            "file_path": file_path
                        }
                    
                    # Wait for file to load
                    time.sleep(2)
                    
                    # Get available analyzers
                    analyzers = self.saleae.get_available_analyzers()
                    logger.info(f"Available analyzers: {analyzers}")
                    
                    # Try to detect protocols
                    detected_protocols = []
                    for analyzer in analyzers:
                        try:
                            # Try to add analyzer
                            self.saleae.add_analyzer(analyzer)
                            logger.info(f"Added analyzer: {analyzer}")
                            detected_protocols.append(analyzer)
                        except Exception as e:
                            logger.warning(f"Failed to add analyzer {analyzer}: {str(e)}")
                    
                    return {
                        "status": "success",
                        "message": "Protocol detection completed",
                        "file_type": "logicdata",
                        "file_path": file_path,
                        "available_analyzers": analyzers,
                        "detected_protocols": detected_protocols
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to detect protocols: {str(e)}")
                    return {
                        "status": "error",
                        "message": f"Failed to detect protocols: {str(e)}",
                        "file_path": file_path
                    }
            else:
                logger.error(f"Unsupported file format: {ext}")
                return {
                    "status": "error",
                    "message": f"Unsupported file format: {ext}",
                    "file_path": file_path
                }

        except Exception as e:
            logger.error(f"Failed to detect protocols: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "file_path": file_path
            }

    def get_digital_data_mcp(self, 
                           input_file: str,
                           digital_channels: Optional[List[int]] = None,
                           time_span: Optional[List[float]] = None) -> Dict[str, Any]:
        """Get digital data from a capture file."""
        try:
            # Verify input file exists
            if not os.path.exists(input_file):
                logger.error(f"Input file not found: {input_file}")
                return {
                    "status": "error",
                    "message": "Input file not found",
                    "details": f"File does not exist: {input_file}"
                }

            # Verify file extension
            if not input_file.lower().endswith(('.logicdata')):
                logger.error(f"Invalid file extension: {input_file}")
                return {
                    "status": "error",
                    "message": "Invalid file extension",
                    "details": "File must have .logicdata extension"
                }

            # Ensure we're connected to Logic
            if not self.connect():
                return {
                    "status": "error",
                    "message": "Failed to connect to Logic",
                    "details": "Please make sure Logic software is running and try again"
                }

            # First, try to open the file in Logic
            logger.info(f"Opening capture file in Logic: {input_file}")
            try:
                # Convert path to forward slashes and make it absolute
                input_file = os.path.abspath(input_file).replace('\\', '/')
                
                logger.info(f"Loading file: {input_file}")
                self.saleae.load_from_file(input_file)
                logger.info("Successfully opened capture file")
                
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                logger.error(f"Failed to open file: {error_type}: {error_msg}")
                return {
                    "status": "error",
                    "message": "Failed to open file",
                    "details": f"{error_type}: {error_msg}"
                }
            
            # Wait for file to load
            logger.info("Waiting for file to load...")
            time.sleep(2)
            
            # Wait for processing to complete
            try:
                logger.info("Waiting for processing to complete...")
                while not self.saleae.is_processing_complete():
                    time.sleep(0.1)
                logger.info("Processing completed")
            except Exception as e:
                logger.error(f"Error waiting for processing: {str(e)}")
                return {
                    "status": "error",
                    "message": "Failed to process file",
                    "details": str(e)
                }
            
            # Get digital data
            try:
                logger.info("Getting digital data...")
                # Create a temporary CSV file
                temp_csv = os.path.splitext(input_file)[0] + "_temp.csv"
                
                # Export digital data to CSV
                self.saleae.export_data2(
                    temp_csv,
                    digital_channels=digital_channels,
                    time_span=time_span,
                    format='csv'
                )
                
                # Wait for export to complete
                while not self.saleae.is_processing_complete():
                    time.sleep(0.1)
                
                # Read and parse the exported data
                digital_data = []
                with open(temp_csv, 'r') as f:
                    # Skip header
                    next(f)
                    for line in f:
                        timestamp, value = line.strip().split(',')
                        digital_data.append({
                            'time': float(timestamp),
                            'value': int(value)
                        })
                
                # Clean up temp file
                os.remove(temp_csv)
                
                logger.info("Successfully got digital data")
                return {
                    "status": "success",
                    "message": "Successfully got digital data",
                    "data": digital_data
                }
            except Exception as e:
                logger.error(f"Error getting digital data: {str(e)}")
                return {
                    "status": "error",
                    "message": "Failed to get digital data",
                    "details": str(e)
                }
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"Failed to get digital data: {error_type}: {error_msg}")
            return {
                "status": "error",
                "message": "Failed to get digital data",
                "details": f"{error_type}: {error_msg}"
            } 