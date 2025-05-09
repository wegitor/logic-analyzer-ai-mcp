from typing import List, Optional, Dict
from saleae.automation import Manager, LogicDeviceConfiguration, CaptureConfiguration, TimedCaptureMode, DeviceType

class Logic2AutomationController:
    """Controller for managing Logic 2 automation device configurations and captures."""
    
    def __init__(self, manager: Manager):
        """
        Initialize the Logic 2 automation controller.
        
        Args:
            manager (Manager): Logic 2 automation manager instance
        """
        self.manager = manager
        self._device_configs: Dict[str, LogicDeviceConfiguration] = {}
        self._capture_configs: Dict[str, CaptureConfiguration] = {}
        
    def create_device_config(self, 
                           name: str,
                           digital_channels: List[int],
                           digital_sample_rate: int,
                           analog_channels: Optional[List[int]] = None,
                           analog_sample_rate: Optional[int] = None,
                           digital_threshold_volts: Optional[float] = None) -> str:
        """
        Create a new device configuration.
        
        Args:
            name (str): Name for the configuration
            digital_channels (List[int]): List of digital channels to enable
            digital_sample_rate (int): Digital sample rate in Hz
            analog_channels (List[int], optional): List of analog channels to enable
            analog_sample_rate (int, optional): Analog sample rate in Hz
            digital_threshold_volts (float, optional): Digital threshold voltage
            
        Returns:
            str: Configuration name
        """
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
        """
        Create a new capture configuration.
        
        Args:
            name (str): Name for the configuration
            duration_seconds (float): Capture duration in seconds
            buffer_size_megabytes (int, optional): Buffer size in MB
            
        Returns:
            str: Configuration name
        """
        config = CaptureConfiguration(
            capture_mode=TimedCaptureMode(duration_seconds=duration_seconds),
            buffer_size_megabytes=buffer_size_megabytes
        )
        self._capture_configs[name] = config
        return name
        
    def get_device_config(self, name: str) -> Optional[LogicDeviceConfiguration]:
        """Get a device configuration by name."""
        return self._device_configs.get(name)
        
    def get_capture_config(self, name: str) -> Optional[CaptureConfiguration]:
        """Get a capture configuration by name."""
        return self._capture_configs.get(name)
        
    def list_device_configs(self) -> List[str]:
        """List all available device configurations."""
        return list(self._device_configs.keys())
        
    def list_capture_configs(self) -> List[str]:
        """List all available capture configurations."""
        return list(self._capture_configs.keys())
        
    def remove_device_config(self, name: str) -> bool:
        """Remove a device configuration."""
        if name in self._device_configs:
            del self._device_configs[name]
            return True
        return False
        
    def remove_capture_config(self, name: str) -> bool:
        """Remove a capture configuration."""
        if name in self._capture_configs:
            del self._capture_configs[name]
            return True
        return False
        
    def get_available_devices(self) -> List[Dict]:
        """
        Get list of available Logic devices.
        
        Returns:
            List[Dict]: List of device information dictionaries with masked device IDs
        """
        devices = self.manager.get_devices()
        return [
            {
                'id': f"{device.device_id[:4]}...{device.device_id[-4:]}" if len(device.device_id) > 8 else "****",
                'type': device.device_type,
                'is_simulation': device.is_simulation
            }
            for device in devices
        ]
        
    def find_device_by_type(self, device_type: DeviceType) -> Optional[Dict]:
        """
        Find a device by its type.
        
        Args:
            device_type (DeviceType): Type of device to find
            
        Returns:
            Optional[Dict]: Device information if found, None otherwise
            
        Raises:
            ValueError: If the device type is not supported
        """
        # Check if device type is supported
        if device_type in [DeviceType.LOGIC, DeviceType.LOGIC_4, DeviceType.LOGIC_16]:
            raise ValueError(f"Device type {device_type.name} is not supported by Logic 2 software")
            
        devices = self.get_available_devices()
        for device in devices:
            if device['type'] == device_type:
                return device
        return None
