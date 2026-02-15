from typing import List, Optional, Dict
from saleae.automation import Manager, LogicDeviceConfiguration, CaptureConfiguration, TimedCaptureMode, DeviceType
import os
import logging

logger = logging.getLogger(__name__)

class Logic2AutomationController:
    """Controller for managing Logic 2 automation device configurations and captures."""
    
    def __init__(self, manager: Optional[Manager] = None):
        self.manager = manager
        self._device_configs: Dict[str, LogicDeviceConfiguration] = {}
        self._capture_configs: Dict[str, CaptureConfiguration] = {}
        self._active_capture = None
        self._analyzers = {}  # Map label -> AnalyzerHandle
        
    def _ensure_manager(self):
        """Check that manager is connected, raise clear error if not."""
        if self.manager is None:
            raise ConnectionError(
                "Not connected to Logic 2. Make sure Logic 2 is running with "
                "automation enabled (Preferences > Enable automation, or launch with --automation flag)"
            )
    
    def reconnect(self, port=10430, timeout=5.0) -> bool:
        """Attempt to (re)connect to Logic 2."""
        try:
            self.manager = Manager.connect(port=port, address='127.0.0.1', connect_timeout_seconds=timeout)
            logger.info(f"Connected to Logic 2 on port {port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Logic 2: {e}")
            return False

    def create_device_config(self, 
                           name: str,
                           digital_channels: List[int],
                           digital_sample_rate: int,
                           analog_channels: Optional[List[int]] = None,
                           analog_sample_rate: Optional[int] = None,
                           digital_threshold_volts: Optional[float] = None) -> str:
        config = LogicDeviceConfiguration(
            enabled_digital_channels=digital_channels,
            digital_sample_rate=digital_sample_rate,
            enabled_analog_channels=analog_channels or [],
            analog_sample_rate=analog_sample_rate,
            digital_threshold_volts=digital_threshold_volts
        )
        self._device_configs[name] = config
        return name
        
    def create_capture_config(self,
                            name: str,
                            duration_seconds: float,
                            buffer_size_megabytes: Optional[int] = None) -> str:
        config = CaptureConfiguration(
            capture_mode=TimedCaptureMode(duration_seconds=duration_seconds),
            buffer_size_megabytes=buffer_size_megabytes
        )
        self._capture_configs[name] = config
        return name
        
    def get_device_config(self, name: str) -> Optional[LogicDeviceConfiguration]:
        return self._device_configs.get(name)
        
    def get_capture_config(self, name: str) -> Optional[CaptureConfiguration]:
        return self._capture_configs.get(name)
        
    def list_device_configs(self) -> List[str]:
        return list(self._device_configs.keys())
        
    def list_capture_configs(self) -> List[str]:
        return list(self._capture_configs.keys())
        
    def remove_device_config(self, name: str) -> bool:
        if name in self._device_configs:
            del self._device_configs[name]
            return True
        return False
        
    def remove_capture_config(self, name: str) -> bool:
        if name in self._capture_configs:
            del self._capture_configs[name]
            return True
        return False
        
    def get_available_devices(self) -> List[Dict]:
        self._ensure_manager()
        devices = self.manager.get_devices(include_simulation_devices=True)
        return [
            {
                'id': str(device.device_id),
                'type': str(device.device_type),
                'is_simulation': device.is_simulation
            }
            for device in devices
        ]
        
    def find_device_by_type(self, device_type: DeviceType) -> Optional[Dict]:
        self._ensure_manager()
        devices = self.get_available_devices()
        for device in devices:
            if device['type'] == str(device_type):
                return device
        return None

    def start_capture(self, 
                     device_config_name: str,
                     capture_config_name: str,
                     device_id: Optional[str] = None) -> Dict:
        """Start a capture using named configurations."""
        self._ensure_manager()
        
        dev_cfg = self._device_configs.get(device_config_name)
        if not dev_cfg:
            raise ValueError(f"Device config '{device_config_name}' not found")
        
        cap_cfg = self._capture_configs.get(capture_config_name)
        if not cap_cfg:
            raise ValueError(f"Capture config '{capture_config_name}' not found")
        
        self._active_capture = self.manager.start_capture(
            device_id=device_id,
            device_configuration=dev_cfg,
            capture_configuration=cap_cfg
        )
        return {"status": "capture_started"}

    def wait_capture(self) -> Dict:
        """Wait for the active capture to complete."""
        if self._active_capture is None:
            raise RuntimeError("No active capture")
        self._active_capture.wait()
        return {"status": "capture_complete"}

    def save_capture(self, filepath: str) -> Dict:
        """Save the active capture to a file."""
        if self._active_capture is None:
            raise RuntimeError("No active capture")
        self._active_capture.save_capture(filepath=filepath)
        return {"status": "saved", "filepath": filepath}

    def export_raw_data(self, directory: str, analog_channels: Optional[List[int]] = None, 
                        digital_channels: Optional[List[int]] = None) -> Dict:
        """Export raw data from active capture to CSV."""
        if self._active_capture is None:
            raise RuntimeError("No active capture")
        
        from saleae.automation import AnalogChannelExportType
        
        os.makedirs(directory, exist_ok=True)
        
        export_config = {}
        if analog_channels is not None:
            from saleae.automation import ExportDataConfiguration, ExportRawDataCsvConfiguration
            self._active_capture.export_raw_data_csv(
                directory=directory,
                analog_channels=analog_channels,
                digital_channels=digital_channels
            )
        
        return {"status": "exported", "directory": directory}

    def close_capture(self):
        """Close the active capture."""
        if self._active_capture is not None:
            self._active_capture.close()
            self._active_capture = None

    def start_capture_with_trigger(self,
                                 device_config_name: str,
                                 trigger_channel_index: int,
                                 trigger_type: str,
                                 after_trigger_seconds: float = 5.0,
                                 trim_data_seconds: Optional[float] = None,
                                 device_id: Optional[str] = None) -> Dict:
        """Start a capture using a digital trigger."""
        self._ensure_manager()
        
        dev_cfg = self._device_configs.get(device_config_name)
        if not dev_cfg:
            raise ValueError(f"Device config '{device_config_name}' not found")
            
        from saleae.automation import CaptureConfiguration, DigitalTriggerCaptureMode, DigitalTriggerType
        
        # Parse trigger type string to enum
        try:
            trig_enum = getattr(DigitalTriggerType, trigger_type.upper())
        except AttributeError:
            raise ValueError(f"Invalid trigger type: {trigger_type}. Must be one of: RISING, FALLING, PULSE_HIGH, PULSE_LOW")
            
        cap_cfg = CaptureConfiguration(
            capture_mode=DigitalTriggerCaptureMode(
                trigger_type=trig_enum,
                trigger_channel_index=trigger_channel_index,
                after_trigger_seconds=after_trigger_seconds,
                trim_data_seconds=trim_data_seconds
            )
        )
        
        self._active_capture = self.manager.start_capture(
            device_id=device_id,
            device_configuration=dev_cfg,
            capture_configuration=cap_cfg
        )
        return {"status": "capture_started", "trigger": f"{trigger_type} on channel {trigger_channel_index}"}

    def add_analyzer(self, analyzer_name: str, label: str, settings: Dict[str, Any]) -> str:
        """Add a protocol analyzer to the active capture."""
        if self._active_capture is None:
            raise RuntimeError("No active capture")
            
        handle = self._active_capture.add_analyzer(analyzer_name, label=label, settings=settings)
        self._analyzers[label] = handle
        return label

    def export_analyzer_data(self, filepath: str, analyzer_label: str) -> Dict:
        """Export data from a specific analyzer to a CSV file."""
        if self._active_capture is None:
            raise RuntimeError("No active capture")
            
        handle = self._analyzers.get(analyzer_label)
        if not handle:
            raise ValueError(f"Analyzer with label '{analyzer_label}' not found (or not added via MCP)")

        from saleae.automation import DataTableExportConfiguration
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        self._active_capture.export_data_table(
            filepath=filepath,
            analyzers=[handle]
        )
        return {"status": "exported", "filepath": filepath}

