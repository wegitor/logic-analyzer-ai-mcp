from typing import List, Dict, Optional, Union, Any
from mcp.server.fastmcp import FastMCP
from saleae import Saleae
from saleae.automation import Manager, Capture
import time
import os
import logging
import json

logger = logging.getLogger(__name__)

class SaleaeParserController:
    """Controller for Saleae Logic capture file parsing using both python-saleae API and Logic 2.x Automation API."""
    
    def __init__(self, mcp: FastMCP):
        """
        Initialize the Saleae parser controller.
        
        Args:
            mcp (FastMCP): MCP server instance
        """
        self.mcp = mcp
        self.saleae = None
        self.manager = None
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        
        # Try to initialize both APIs
        try:
            # Initialize python-saleae API
            self.saleae = Saleae()
            logger.info("Successfully initialized python-saleae API")
            
            # Initialize Logic 2.x Automation API
            self.manager = Manager.connect()
            logger.info("Successfully initialized Logic 2.x Automation API")
        except Exception as e:
            logger.warning(f"Could not initialize Saleae APIs: {e}")
            logger.warning("File parsing will be limited to offline mode")
        
    def _check_file_format(self, file_path: str) -> str:
        """Check if the file is a .sal or .logicdata file."""
        if not file_path:
            raise ValueError("No file path provided")
        
        if not os.path.exists(file_path):
            raise ValueError(f"File does not exist: {file_path}")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in ['.sal', '.logicdata']:
            raise ValueError(f"Unsupported file format: {file_ext}. Only .sal and .logicdata files are supported.")
        
        return 'sal' if file_ext == '.sal' else 'logicdata'
    
    def _ensure_connection(self, file_format: str):
        """Ensure connection to Logic software, launching if necessary."""
        if file_format == 'sal':
            if self.manager is None:
                logger.warning("Logic 2.x Automation API is not available. Operation will be limited to offline mode.")
                return
            return
        
        # For logicdata format
        if self.saleae is None:
            try:
                self.saleae = Saleae()
                logger.info("Successfully initialized python-saleae API")
            except Exception as e:
                logger.error(f"Failed to initialize python-saleae API: {e}")
                return
        
        retries = 0
        while retries < self.max_retries:
            try:
                self.saleae.connect()
                logger.info("Successfully connected to Logic software")
                return
            except Exception as e:
                if "Could not connect to Logic software" in str(e):
                    try:
                        self.saleae.launch_logic()
                        time.sleep(self.retry_delay)
                        logger.info("Successfully launched Logic software")
                        return
                    except Exception as launch_error:
                        logger.error(f"Failed to launch Logic software: {launch_error}")
                        return
                logger.error(f"Connection error: {e}")
                retries += 1
                if retries < self.max_retries:
                    time.sleep(self.retry_delay)
        
        logger.error("Failed to connect to Logic software after maximum retries")
        
    def parse_capture_file(self, 
                          capture_file: Optional[str] = None,
                          data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Initialize parser with a capture file or direct data and return basic information.
        
        Args:
            capture_file: Path to the capture file (optional)
            data: Direct data dictionary with duration, digital_channels, and analog_channels (optional)
            
        Returns:
            Dict[str, Any]: Basic information about the capture file
        """
        try:
            if not capture_file:
                return {
                    "status": "error",
                    "message": "No capture file provided",
                    "details": "Either capture_file or data parameter must be provided"
                }
            
            # Check file format
            file_format = self._check_file_format(capture_file)
            
            # Ensure connection based on file format
            self._ensure_connection(file_format)
            
            if file_format == 'sal':
                if not self.manager:
                    return {
                        "status": "error",
                        "message": "Logic 2.x Automation API is not available",
                        "details": "Please ensure Logic 2.x software is installed and running"
                    }
                
                # Use Logic 2.x API to get file info
                with self.manager.load_capture(capture_file) as capture:
                    return {
                        "status": "success",
                        "file_info": {
                            "path": capture_file,
                            "format": "Saleae Logic 2.x (.sal)",
                            "duration": capture.duration,
                            "digital_channels": list(range(capture.digital_channel_count)),
                            "analog_channels": list(range(capture.analog_channel_count)),
                            "digital_sample_rate": capture.digital_sample_rate,
                            "analog_sample_rate": capture.analog_sample_rate
                        }
                    }
            else:  # logicdata
                if not self.saleae:
                    return {
                        "status": "error",
                        "message": "python-saleae API is not available",
                        "details": "Please ensure Logic software is installed and running"
                    }
                
                # Use python-saleae API to get file info
                self.saleae.load_from_file(capture_file)
                
                # Wait for processing to complete
                while not self.saleae.is_processing_complete():
                    time.sleep(0.1)
                
                return {
                    "status": "success",
                    "file_info": {
                        "path": capture_file,
                        "format": "Saleae Logic 1.x (.logicdata)",
                        "duration": self.saleae.get_capture_seconds(),
                        "digital_channels": self.saleae.get_active_channels()[0],
                        "analog_channels": self.saleae.get_active_channels()[1],
                        "digital_sample_rate": self.saleae.get_sample_rate()[0],
                        "analog_sample_rate": self.saleae.get_sample_rate()[1]
                    }
                }
        except ValueError as e:
                return {
                    "status": "error",
                "message": str(e),
                "details": "Only .sal and .logicdata files are supported"
                }
        except Exception as e:
            logger.error(f"Error parsing file: {e}")
            return {
                "status": "error",
                "message": "Failed to parse file",
                "details": str(e)
            }
        
    def get_digital_data(self, 
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
            if not capture_file:
                return {
                    "status": "error",
                    "message": "No capture file provided",
                    "details": "Saleae API requires a capture file for data extraction"
                }
            
            # Check file format
            file_format = self._check_file_format(capture_file)
            
            # Ensure connection based on file format
            self._ensure_connection(file_format)
            
            if not self.saleae:
                return {
                    "status": "error",
                    "message": "python-saleae API is not available",
                    "details": "Please ensure Logic software is installed and running"
                }
            
            # Use python-saleae API to get digital data
            self.saleae.load_from_file(capture_file)
            
            # Wait for processing to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)
            
            # Export digital data for the specified channel
            temp_file = "temp_digital_export.csv"
            self.saleae.export_data2(
                temp_file,
                digital_channels=[channel],
                format='csv',
                csv_column_headers=True,
                csv_timestamp='time_stamp',
                csv_combined=True,
                csv_row_per_change=True
            )
            
            # Wait for export to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)
            
            # Read and parse the exported data
            digital_data = []
            with open(temp_file, 'r') as f:
                # Skip header
                next(f)
                for line in f:
                    timestamp, value = line.strip().split(',')
                    digital_data.append({
                        'time': float(timestamp),
                        'value': int(value)
                    })
            
            # Clean up temp file
            os.remove(temp_file)
            
            # Filter by time range if specified
            if start_time is not None or end_time is not None:
                digital_data = [
                    point for point in digital_data
                    if (start_time is None or point['time'] >= start_time) and
                       (end_time is None or point['time'] <= end_time)
                ]
            
            return {
                "status": "success",
                "data": digital_data
            }
        except ValueError as e:
            return {
                "status": "error",
                "message": str(e),
                "details": "Only .sal and .logicdata files are supported"
            }
        except Exception as e:
            logger.error(f"Error getting digital data: {e}")
            return {
                "status": "error",
                "message": "Failed to get digital data",
                "details": str(e)
            }
        
    def get_analog_data(self, 
                       capture_file: Optional[str] = None,
                       data: Optional[List[Dict[str, Union[float, float]]]] = None,
                       channel: int = 0,
                       start_time: Optional[float] = None,
                       end_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Get analog data for a specific channel.
        
        Args:
            capture_file: Path to the capture file (optional)
            data: Direct data list of samples (optional)
            channel: Channel number
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)
        """
        try:
            if not capture_file:
                return {
                    "status": "error",
                    "message": "No capture file provided",
                    "details": "Saleae API requires a capture file for data extraction"
                }
            
            # Check file format
            file_format = self._check_file_format(capture_file)
            
            # Ensure connection based on file format
            self._ensure_connection(file_format)
            
            if not self.saleae:
                return {
                    "status": "error",
                    "message": "python-saleae API is not available",
                    "details": "Please ensure Logic software is installed and running"
                }
            
            # Use python-saleae API to get analog data
            self.saleae.load_from_file(capture_file)
            
            # Wait for processing to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)
            
            # Export analog data for the specified channel
            temp_file = "temp_analog_export.csv"
            self.saleae.export_data2(
                temp_file,
                analog_channels=[channel],
                format='csv',
                csv_column_headers=True,
                csv_timestamp='time_stamp',
                csv_combined=True,
                csv_row_per_change=True
            )
            
            # Wait for export to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)
            
            # Read and parse the exported data
            analog_data = []
            with open(temp_file, 'r') as f:
                # Skip header
                next(f)
                for line in f:
                    timestamp, value = line.strip().split(',')
                    analog_data.append({
                        'time': float(timestamp),
                        'value': float(value)
                    })
            
            # Clean up temp file
            os.remove(temp_file)
            
            # Filter by time range if specified
            if start_time is not None or end_time is not None:
                analog_data = [
                    point for point in analog_data
                    if (start_time is None or point['time'] >= start_time) and
                       (end_time is None or point['time'] <= end_time)
                ]
            
            return {
                "status": "success",
                "data": analog_data
            }
        except ValueError as e:
            return {
                "status": "error",
                "message": str(e),
                "details": "Only .sal and .logicdata files are supported"
            }
        except Exception as e:
            logger.error(f"Error getting analog data: {e}")
            return {
                "status": "error",
                "message": "Failed to get analog data",
                "details": str(e)
            }
        
    def export_data(self, 
                   capture_file: Optional[str] = None,
                   data: Optional[Dict[str, Any]] = None,
                   output_file: str = "exported_data.csv",
                   format: str = "csv",
                   digital_channels: Optional[List[int]] = None,
                   analog_channels: Optional[List[int]] = None,
                   start_time: Optional[float] = None,
                   end_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Export data from a capture file.
        
        Args:
            capture_file: Path to the capture file (optional)
            data: Direct data dictionary (optional)
            output_file: Path to save the exported data
            format: Export format ('csv', 'binary', 'vcd', 'matlab')
            digital_channels: List of digital channels to export
            analog_channels: List of analog channels to export
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)
        """
        try:
            if not capture_file:
                return {
                    "status": "error",
                    "message": "No capture file provided",
                    "details": "Saleae API requires a capture file for data export"
                }
            
            # Check file format
            file_format = self._check_file_format(capture_file)
            
            # Ensure connection based on file format
            self._ensure_connection(file_format)
            
            if not self.saleae:
                return {
                    "status": "error",
                    "message": "python-saleae API is not available",
                    "details": "Please ensure Logic software is installed and running"
                }
            
            # Use python-saleae API to export data
            self.saleae.load_from_file(capture_file)
            
            # Wait for processing to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)
            
            # Export data using export_data2
            self.saleae.export_data2(
                output_file,
                digital_channels=digital_channels,
                analog_channels=analog_channels,
                format=format,
                csv_column_headers=True,
                csv_timestamp='time_stamp',
                csv_combined=True,
                csv_row_per_change=True
            )
            
            # Wait for export to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)
            
            return {
                "status": "success",
                "message": f"Data exported to {output_file}",
                "format": format,
                "channels": {
                    "digital": digital_channels,
                    "analog": analog_channels
                }
            }
        except ValueError as e:
            return {
                "status": "error",
                "message": str(e),
                "details": "Only .sal and .logicdata files are supported"
            }
        except ConnectionError as e:
            return {
                "status": "error",
                "message": "Failed to connect to Logic software",
                "details": str(e)
            }
        except TimeoutError as e:
            return {
                "status": "error",
                "message": "Operation timed out",
                "details": str(e)
            }
        except IOError as e:
            return {
                "status": "error",
                "message": "File I/O error",
                "details": str(e)
            }
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return {
                "status": "error",
                "message": "Failed to export data",
                "details": str(e)
            }
        
    def get_sample_rate(self, 
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
            if not capture_file:
                return {
                    "status": "error",
                    "message": "No capture file provided",
                    "details": "Saleae API requires a capture file to get sample rate"
                }
            
            if not self.saleae:
                return {
                    "status": "error",
                    "message": "Saleae software is not available",
                    "details": "Please ensure Saleae Logic software is installed and running"
                }
            
            # Connect to Saleae software
            self._ensure_connection('logicdata')
            
            # Load the capture file
            self.saleae.load_from_file(capture_file)
            
            # Wait for processing to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)
            
            # Get sample rate based on channel type
            digital_channels, analog_channels = self.saleae.get_active_channels()
            if channel < len(digital_channels):
                sample_rate = self.saleae.get_sample_rate()[0]  # Digital sample rate
            else:
                sample_rate = self.saleae.get_sample_rate()[1]  # Analog sample rate
            
            return {
                "status": "success",
                "sample_rate": sample_rate
            }
        except Exception as e:
            logger.error(f"Error getting sample rate: {e}")
            return {
                "status": "error",
                "message": "Failed to get sample rate",
                "details": str(e)
            } 