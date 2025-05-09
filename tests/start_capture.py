import os
import sys
import time
import logging
from saleae import Saleae
import argparse
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_saleae_paths():
    """Check all possible Saleae Logic installation paths."""
    common_paths = [
        # Logic 1 paths (older version)
        os.path.expandvars(r"%ProgramFiles%\Saleae\Logic\Logic.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Saleae\Logic\Logic.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Saleae\Logic\Logic.exe"),
        # Logic 2 paths (newer version)
        os.path.expandvars(r"%ProgramFiles%\Saleae\Logic2\Logic2.exe"),
        os.path.expandvars(r"%ProgramFiles%\Logic2\Logic2.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Saleae\Logic2\Logic2.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Saleae\Logic2\Logic2.exe"),
        # Legacy paths
        os.path.expandvars(r"%ProgramFiles%\Logic\Logic.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Logic\Logic.exe")
    ]
    
    logger.info("Checking Saleae Logic installation paths...")
    found_paths = []
    
    for path in common_paths:
        logger.info(f"Checking path: {path}")
        if os.path.exists(path):
            logger.info(f"✓ Found at: {path}")
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
                found_paths.append(path)
            except Exception as e:
                logger.error(f"  ✗ Error checking permissions: {str(e)}")
        else:
            logger.info(f"✗ Not found at: {path}")
    
    if not found_paths:
        logger.error("No Saleae Logic installation found!")
        logger.info("Please install Saleae Logic from: https://www.saleae.com/downloads/")
        logger.info("After installation, try running the script again.")
    
    return found_paths

def try_launch_saleae(path):
    """Try to launch Saleae Logic using different methods."""
    logger.info(f"\nAttempting to launch Saleae Logic from: {path}")
    
    # First check if Logic is already running
    try:
        saleae = Saleae()
        devices = saleae.get_connected_devices()
        logger.info("✓ Logic is already running")
        return True
    except Exception:
        logger.info("Logic is not running, attempting to launch...")
    
    # Method 1: Using subprocess with elevated privileges
    try:
        logger.info("Method 1: Using subprocess.Popen with elevated privileges...")
        if os.name == 'nt':  # Windows
            # Try to launch with elevated privileges
            process = subprocess.Popen(
                [path],
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            process = subprocess.Popen([path])
        logger.info("✓ Process started")
        time.sleep(5)  # Wait for initial startup
        
        # Verify process is running
        if process.poll() is None:
            logger.info("✓ Process is running")
            # Wait for Logic to initialize
            time.sleep(10)  # Give more time for Logic to fully initialize
            return True
        else:
            logger.error("✗ Process exited immediately")
            return False
            
    except Exception as e:
        logger.error(f"✗ Subprocess launch failed: {str(e)}")
    
    # Method 2: Using Saleae API
    try:
        logger.info("Method 2: Using Saleae API...")
        saleae = Saleae()
        saleae.launch()
        logger.info("✓ API launch attempted")
        time.sleep(10)  # Wait longer for startup
        return True
    except Exception as e:
        logger.error(f"✗ API launch failed: {str(e)}")
    
    return False

def verify_capture_running(saleae, timeout=5):
    """Verify that capture is actually running."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            state = get_device_state(saleae)
            logger.info(f"Current device state: {state}")
            
            if state.get('is_capturing'):
                logger.info("Capture is running")
                return True
                
            # Try to start capture again if not running
            if not state.get('is_capturing'):
                logger.info("Attempting to start capture...")
                saleae.start_capture()
                time.sleep(0.5)
                
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error checking capture status: {str(e)}")
            return False
    return False

def verify_device_ready(saleae, timeout=10):
    """Verify that device is ready for capture."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            devices = saleae.get_connected_devices()
            if devices:
                # Try to get device status
                try:
                    # Check if device is in a good state
                    if saleae.is_processing_complete():  # Not currently processing
                        if not saleae.is_capture_running():  # Not currently capturing
                            return True
                except Exception as e:
                    logger.warning(f"Error checking device status: {str(e)}")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error verifying device: {str(e)}")
    return False

def get_device_state(saleae):
    """Get detailed device state information."""
    try:
        state = {
            'is_processing': not saleae.is_processing_complete(),
            'is_capturing': saleae.is_capture_running(),
            'devices': saleae.get_connected_devices(),
            'sample_rate': saleae.get_sample_rate(),
            'active_channels': saleae.get_active_channels(),
            'capture_seconds': saleae.get_capture_seconds(),
            'is_connected': saleae.is_connected()
        }
        return state
    except Exception as e:
        return {'error': str(e)}

def reset_device_state(saleae):
    """Reset device to a known good state."""
    try:
        logger.info("Resetting device state...")
        
        # Wait a moment for device to stabilize
        time.sleep(0.5)
        
        # Try to reset sample rate to a known good value
        try:
            # Get available sample rates first
            sample_rates = saleae.get_all_sample_rates()
            if sample_rates:
                # Use the lowest rate for safety
                safe_rate = min(sample_rates)
                saleae.set_sample_rate(safe_rate)
                logger.info(f"Reset sample rate to {safe_rate}")
        except Exception as e:
            logger.warning(f"Failed to reset sample rate: {str(e)}")
            
        # Try to reset channels to a minimal set
        try:
            saleae.set_active_channels([0], [])  # Just channel 0
        except Exception as e:
            logger.warning(f"Failed to reset channels: {str(e)}")
            
        logger.info("Device state reset complete")
        return True
        
    except Exception as e:
        logger.error(f"Failed to reset device: {str(e)}")
        return False

def wait_for_firmware(saleae, timeout=10):
    """Wait for firmware to be properly initialized."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Try to get device info to check if firmware is ready
            devices = saleae.get_connected_devices()
            if devices and "Logic16" in str(devices[0]):
                try:
                    # Try basic operations to verify firmware
                    saleae.get_sample_rate()
                    saleae.get_active_channels()
                    logger.info("Firmware appears to be initialized")
                    return True
                except Exception as e:
                    logger.warning(f"Firmware not ready: {str(e)}")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error checking firmware: {str(e)}")
    return False

def verify_logic16_device(saleae, timeout=10):
    """Verify Logic16 device is properly initialized."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            devices = saleae.get_connected_devices()
            if devices and "Logic16" in str(devices[0]):
                logger.info("Logic16 device detected")
                
                # Try to get device info
                try:
                    # Check if device is responding
                    saleae.get_sample_rate()
                    saleae.get_active_channels()
                    logger.info("Logic16 device is responding")
                    return True
                except Exception as e:
                    logger.warning(f"Device not fully initialized: {str(e)}")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error verifying Logic16: {str(e)}")
    return False

def verify_logicpro16_device(saleae, timeout=10):
    """Verify LogicPro16 device is properly initialized."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            devices = saleae.get_connected_devices()
            if devices and "LogicPro16" in str(devices[0]):
                logger.info("LogicPro16 device detected")
                
                # Try to get device info
                try:
                    # Check if device is responding
                    saleae.get_sample_rate()
                    saleae.get_active_channels()
                    logger.info("LogicPro16 device is responding")
                    return True
                except Exception as e:
                    logger.warning(f"Device not fully initialized: {str(e)}")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error verifying LogicPro16: {str(e)}")
    return False

def configure_logic16_settings(saleae):
    """Configure Logic16 device with proper settings."""
    try:
        logger.info("Configuring Logic16 settings...")
        
        # Get available sample rates
        sample_rates = saleae.get_all_sample_rates()
        if not sample_rates:
            logger.error("Could not get available sample rates")
            return False
            
        # Find the highest supported sample rate
        max_rate = max(sample_rates)
        logger.info(f"Using sample rate: {max_rate}")
        
        # Set sample rate
        try:
            saleae.set_sample_rate(max_rate)
        except Exception as e:
            logger.error(f"Failed to set sample rate: {str(e)}")
            return False
            
        # Enable channels
        try:
            channels = [0, 1, 2, 3]  # First 4 channels
            saleae.set_active_channels(channels, [])
            logger.info(f"Enabled channels {channels}")
        except Exception as e:
            logger.error(f"Failed to set active channels: {str(e)}")
            return False
            
        # Set capture duration
        try:
            saleae.set_capture_seconds(1.0)
        except Exception as e:
            logger.error(f"Failed to set capture duration: {str(e)}")
            return False
            
        logger.info("Successfully configured Logic16 settings")
        return True
        
    except Exception as e:
        logger.error(f"Failed to configure Logic16: {str(e)}")
        return False

def configure_logicpro16_settings(saleae):
    """Configure LogicPro16 with proper settings."""
    try:
        logger.info("Configuring LogicPro16 settings...")
        
        # Set LED first (as seen in logs)
        try:
            saleae.set_led(True)
            logger.info("Set LED on")
            time.sleep(0.2)  # Wait for LED to stabilize
        except Exception as e:
            logger.warning(f"Failed to set LED: {str(e)}")
        
        # Enable channels
        saleae.set_active_channels([0, 1, 2, 3])  # Enable first 4 channels
        logger.info("Enabled channels 0-3")
        time.sleep(0.2)  # Wait for channel configuration
        
        # Set voltage threshold (as seen in logs)
        try:
            saleae.set_digital_voltage_threshold(1.65)  # Default threshold
            logger.info("Set voltage threshold")
            time.sleep(0.2)  # Wait for threshold to stabilize
        except Exception as e:
            logger.warning(f"Failed to set voltage threshold: {str(e)}")
        
        # Set proper sample rate (16MHz as seen in logs)
        saleae.set_sample_rate(16000000)
        logger.info("Set sample rate to 16MHz")
        time.sleep(0.2)  # Wait for sample rate to stabilize
        
        # Set capture duration
        saleae.set_capture_seconds(1.0)
        logger.info("Set capture duration to 1 second")
        
        # Verify settings
        try:
            rate = saleae.get_sample_rate()
            channels = saleae.get_active_channels()
            logger.info(f"Settings verified - Rate: {rate}, Channels: {channels}")
            return True
        except Exception as e:
            logger.error(f"Failed to verify settings: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to configure LogicPro16: {str(e)}")
        return False

def initialize_logic16(saleae):
    """Initialize Logic16 device with proper settings."""
    try:
        logger.info("Initializing Logic16 device...")
        
        # Wait for firmware
        if not wait_for_firmware(saleae):
            logger.error("Firmware initialization failed")
            return False
        
        # Configure with proper settings
        if not configure_logic16_settings(saleae):
            logger.error("Failed to configure device settings")
            return False
            
        logger.info("Device initialized successfully")
        return True
            
    except Exception as e:
        logger.error(f"Failed to initialize Logic16: {str(e)}")
        return False

def initialize_logicpro16(saleae):
    """Initialize LogicPro16 device with proper settings."""
    try:
        logger.info("Initializing LogicPro16 device...")
        
        # Wait for firmware
        if not wait_for_firmware(saleae):
            logger.error("Firmware initialization failed")
            return False
        
        # Try to reset device first
        try:
            logger.info("Attempting device reset...")
            saleae.stop_capture()
            time.sleep(1)
        except Exception as e:
            logger.warning(f"Reset attempt failed: {str(e)}")
        
        # Configure with proper settings
        if not configure_logicpro16_settings(saleae):
            logger.error("Failed to configure device settings")
            return False
        
        # Try a minimal capture to verify
        logger.info("Testing capture...")
        saleae.start_capture()
        time.sleep(0.2)
        if saleae.is_capture_running():
            logger.info("Capture test successful")
            saleae.stop_capture()
            return True
        else:
            logger.error("Capture test failed")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize LogicPro16: {str(e)}")
        return False

def force_capture_start(saleae, max_attempts=3):
    """Force capture to start with multiple attempts."""
    for attempt in range(max_attempts):
        try:
            # Reset device state first
            if not reset_device_state(saleae):
                logger.error("Failed to reset device state")
                continue
            
            # Get initial state
            initial_state = get_device_state(saleae)
            logger.info(f"Initial device state: {initial_state}")
            
            # Try to start capture with different methods
            logger.info(f"Capture attempt {attempt + 1}: Starting capture...")
            
            # Method 1: Direct start with proper settings
            try:
                logger.info("Method 1: Using proper settings...")
                if configure_logic16_settings(saleae):
                    # Try to start capture multiple times
                    for _ in range(3):
                        saleae.start_capture()
                        time.sleep(0.5)
                        if verify_capture_running(saleae):
                            logger.info("✓ Capture started successfully (Method 1)")
                            return True
                        time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Method 1 failed: {str(e)}")
            
            # Method 2: Stop and start with delay
            try:
                logger.info("Method 2: Stop and start with delay...")
                saleae.stop_capture()
                time.sleep(2)
                if configure_logic16_settings(saleae):
                    # Try to start capture multiple times
                    for _ in range(3):
                        saleae.start_capture()
                        time.sleep(0.5)
                        if verify_capture_running(saleae):
                            logger.info("✓ Capture started successfully (Method 2)")
                            return True
                        time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Method 2 failed: {str(e)}")
            
            # Method 3: Reinitialize and start
            try:
                logger.info("Method 3: Reinitialize and start...")
                if initialize_logic16(saleae):
                    # Try to start capture multiple times
                    for _ in range(3):
                        saleae.start_capture()
                        time.sleep(0.5)
                        if verify_capture_running(saleae):
                            logger.info("✓ Capture started successfully (Method 3)")
                            return True
                        time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Method 3 failed: {str(e)}")
            
            logger.warning(f"All methods failed for attempt {attempt + 1}")
            
        except Exception as e:
            logger.error(f"Capture attempt {attempt + 1} failed: {str(e)}")
        
        if attempt < max_attempts - 1:
            logger.info("Waiting before next attempt...")
            time.sleep(2)
    
    return False

def verify_logic_running(max_attempts=3):
    """Verify that Logic is running and accessible."""
    for attempt in range(max_attempts):
        try:
            logger.info(f"Attempting to connect to Logic (attempt {attempt + 1}/{max_attempts})...")
            # Try to connect to Logic
            saleae = Saleae()
            # Try a simple operation
            saleae.get_connected_devices()
            logger.info("✓ Successfully connected to Logic")
            return True
        except Exception as e:
            logger.error(f"✗ Could not connect to Logic: {str(e)}")
            if attempt < max_attempts - 1:
                logger.info("Waiting before next attempt...")
                time.sleep(5)  # Wait between attempts
    return False

def handle_connection_error(saleae, error):
    """Handle connection errors and attempt recovery."""
    logger.error(f"Connection error: {str(error)}")
    
    # Check for USB permissions error
    if "Access is denied" in str(error):
        logger.error("USB permissions error detected. Please run the script as administrator.")
        logger.info("Try running the script with administrator privileges.")
        return False
        
    # Check for file not found error
    if "The system cannot find the file specified" in str(error):
        logger.error("Could not connect to Logic software.")
        logger.info("This usually means Logic is not running or not accessible.")
        logger.info("Please ensure:")
        logger.info("1. Logic is running (you should see the Logic window)")
        logger.info("2. You have administrator privileges")
        logger.info("3. No other instances of Logic are running")
        return False
    
    try:
        # Try to reset device state
        if saleae:
            saleae.stop_capture()
            time.sleep(1)
        return False
    except Exception as e:
        logger.error(f"Failed to handle connection error: {str(e)}")
        return False

def handle_configuration_error(saleae, error):
    """Handle configuration errors and attempt recovery."""
    logger.error(f"Configuration error: {str(error)}")
    try:
        # Try to reset device state
        if saleae:
            saleae.stop_capture()
            time.sleep(1)
            # Try to reconfigure with minimal settings
            saleae.set_sample_rate(1000000)  # Try lower sample rate
            saleae.set_active_channels([0])  # Try single channel
            saleae.set_capture_seconds(0.1)  # Try shorter capture
            return True
    except Exception as e:
        logger.error(f"Failed to handle configuration error: {str(e)}")
        return False

def handle_capture_error(saleae, error):
    """Handle capture errors and attempt recovery."""
    logger.error(f"Capture error: {str(error)}")
    try:
        # Try to reset device state
        if saleae:
            saleae.stop_capture()
            time.sleep(1)
            # Try to restart capture with minimal settings
            saleae.set_sample_rate(1000000)  # Try lower sample rate
            saleae.set_active_channels([0])  # Try single channel
            saleae.set_capture_seconds(0.1)  # Try shorter capture
            saleae.start_capture()
            time.sleep(0.5)
            if saleae.is_capture_running():
                return True
    except Exception as e:
        logger.error(f"Failed to handle capture error: {str(e)}")
        return False

def connect_to_device():
    """Connect to a Saleae device with retry logic."""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info("Connecting to Saleae Logic...")
            saleae = Saleae()
            
            # Wait for Logic to initialize
            logger.info("Waiting for Logic to initialize...")
            time.sleep(2)
            
            # Check if any device is connected
            devices = saleae.get_connected_devices()
            if not devices:
                logger.error("No devices found")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                return None
                
            # Get the first device
            device = devices[0]
            logger.info(f"Found device: {device}")
            
            # Initialize the device
            if not initialize_logic16(saleae):
                logger.error("Failed to initialize device")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                return None
                
            return saleae
            
        except Exception as e:
            logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Failed to connect to any device")
                return None
                
    return None

class SaleaeCapture:
    def __init__(self, sample_rate=16000000, duration=1.0, channels=None):
        """Initialize Saleae capture settings."""
        self.sample_rate = sample_rate
        self.duration = duration
        self.channels = channels or [0, 1, 2, 3]  # Default to first 4 channels
        self.saleae = None
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        
    def start_capture(self):
        """Start the capture."""
        try:
            logger.info("Starting capture...")
            self.saleae.set_num_samples(1000000000)
            logger.info("Set capture to 1000000000 samples")
            capture_file = os.path.join(os.getcwd(), "capture.logicdata")
            self.saleae.capture_to_file(capture_file)
            logger.info(f"Capture started, saving to {capture_file}")
            # Wait for processing to complete
            while not self.saleae.is_processing_complete():
                time.sleep(0.1)
            logger.info("Capture completed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start capture: {str(e)}")
            return False
            
    def stop_capture(self):
        """Stop the capture."""
        try:
            # In Logic 1.2.40, we can't stop captures programmatically
            # The user will need to stop it manually in the Logic UI
            logger.info("Please stop the capture manually in the Logic UI")
        except Exception as e:
            logger.warning(f"Failed to stop capture: {str(e)}")
            
    def configure_capture(self):
        """Configure capture settings."""
        try:
            logger.info("Configuring capture settings...")
            
            # Get available sample rates
            sample_rates = self.saleae.get_all_sample_rates()
            if not sample_rates:
                logger.error("Could not get available sample rates")
                return False
                
            # Find the highest supported sample rate
            max_rate = max(sample_rates)
            logger.info(f"Using sample rate: {max_rate}")
            
            # Set sample rate
            try:
                self.saleae.set_sample_rate(max_rate)
            except Exception as e:
                logger.error(f"Failed to set sample rate: {str(e)}")
                return False
                
            # Enable channels
            try:
                self.saleae.set_active_channels(self.channels, [])
                logger.info(f"Enabled channels {self.channels}")
            except Exception as e:
                logger.error(f"Failed to set active channels: {str(e)}")
                return False
                
            # Set capture duration
            try:
                self.saleae.set_capture_seconds(self.duration)
            except Exception as e:
                logger.error(f"Failed to set capture duration: {str(e)}")
                return False
                
            logger.info("Successfully configured capture settings")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure capture: {str(e)}")
            return False

def test_export_data2(saleae, capture_file):
    """Test export_data2 functionality with different parameters."""
    try:
        logger.info(f"Testing export_data2 with file: {capture_file}")
        
        # Load the capture file
        saleae.load_from_file(capture_file)
        
        # Wait for processing to complete
        while not saleae.is_processing_complete():
            time.sleep(0.1)
        
        # Get active channels
        active_channels = saleae.get_active_channels()
        digital_channels = active_channels[0]
        analog_channels = active_channels[1]
        
        logger.info(f"Active channels - Digital: {digital_channels}, Analog: {analog_channels}")
        
        test_results = []
        
        # Test 1: Export all channels
        try:
            output_file = os.path.splitext(capture_file)[0] + "_test1.csv"
            logger.info(f"Test 1: Exporting all channels to {output_file}")
            saleae.export_data2(
                output_file,
                digital_channels=digital_channels,
                analog_channels=analog_channels,
                format='csv'
            )
            while not saleae.is_processing_complete():
                time.sleep(0.1)
            test_results.append({
                "test": "Export all channels",
                "status": "success",
                "output_file": output_file
            })
            logger.info("✓ Test 1 completed successfully")
        except Exception as e:
            test_results.append({
                "test": "Export all channels",
                "status": "error",
                "error": str(e)
            })
            logger.error(f"✗ Test 1 failed: {str(e)}")
        
        # Test 2: Export specific digital channels
        if digital_channels:
            try:
                output_file = os.path.splitext(capture_file)[0] + "_test2.csv"
                logger.info(f"Test 2: Exporting channel {digital_channels[0]} to {output_file}")
                saleae.export_data2(
                    output_file,
                    digital_channels=[digital_channels[0]],  # Test with first digital channel
                    format='csv'
                )
                while not saleae.is_processing_complete():
                    time.sleep(0.1)
                test_results.append({
                    "test": "Export specific digital channel",
                    "status": "success",
                    "output_file": output_file
                })
                logger.info("✓ Test 2 completed successfully")
            except Exception as e:
                test_results.append({
                    "test": "Export specific digital channel",
                    "status": "error",
                    "error": str(e)
                })
                logger.error(f"✗ Test 2 failed: {str(e)}")
        
        # Test 3: Export with time span
        try:
            output_file = os.path.splitext(capture_file)[0] + "_test3.csv"
            logger.info(f"Test 3: Exporting with time span to {output_file}")
            saleae.export_data2(
                output_file,
                digital_channels=digital_channels,
                analog_channels=analog_channels,
                time_span=[0.0, 1.0],  # First second of capture
                format='csv'
            )
            while not saleae.is_processing_complete():
                time.sleep(0.1)
            test_results.append({
                "test": "Export with time span",
                "status": "success",
                "output_file": output_file
            })
            logger.info("✓ Test 3 completed successfully")
        except Exception as e:
            test_results.append({
                "test": "Export with time span",
                "status": "error",
                "error": str(e)
            })
            logger.error(f"✗ Test 3 failed: {str(e)}")
        
        # Test 4: Export in different formats
        formats = ['csv', 'vcd', 'matlab']
        for fmt in formats:
            try:
                output_file = os.path.splitext(capture_file)[0] + f"_test4_{fmt}"
                logger.info(f"Test 4: Exporting in {fmt} format to {output_file}")
                saleae.export_data2(
                    output_file,
                    digital_channels=digital_channels,
                    analog_channels=analog_channels,
                    format=fmt
                )
                while not saleae.is_processing_complete():
                    time.sleep(0.1)
                test_results.append({
                    "test": f"Export in {fmt} format",
                    "status": "success",
                    "output_file": output_file
                })
                logger.info(f"✓ Test 4 ({fmt}) completed successfully")
            except Exception as e:
                test_results.append({
                    "test": f"Export in {fmt} format",
                    "status": "error",
                    "error": str(e)
                })
                logger.error(f"✗ Test 4 ({fmt}) failed: {str(e)}")
        
        # Test 5: Export with minimal parameters
        try:
            output_file = os.path.splitext(capture_file)[0] + "_test5.csv"
            logger.info(f"Test 5: Exporting with minimal parameters to {output_file}")
            saleae.export_data2(
                output_file,
                format='csv'
            )
            while not saleae.is_processing_complete():
                time.sleep(0.1)
            test_results.append({
                "test": "Export with minimal parameters",
                "status": "success",
                "output_file": output_file
            })
            logger.info("✓ Test 5 completed successfully")
        except Exception as e:
            test_results.append({
                "test": "Export with minimal parameters",
                "status": "error",
                "error": str(e)
            })
            logger.error(f"✗ Test 5 failed: {str(e)}")
        
        # Print summary
        logger.info("\nExport Test Summary:")
        logger.info("===================")
        for result in test_results:
            status = "✓" if result["status"] == "success" else "✗"
            logger.info(f"{status} {result['test']}")
            if result["status"] == "error":
                logger.info(f"  Error: {result['error']}")
        
        return {
            "status": "success",
            "message": "Export tests completed",
            "active_channels": {
                "digital": digital_channels,
                "analog": analog_channels
            },
            "test_results": test_results
        }
        
    except Exception as e:
        logger.error(f"Failed to run export tests: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to run export tests: {str(e)}"
        }

def main():
    """Main function to handle the capture process."""
    try:
        # First check if Logic is installed
        found_paths = check_saleae_paths()
        if not found_paths:
            logger.error("No Saleae Logic installation found!")
            logger.info("Please install Saleae Logic from: https://www.saleae.com/downloads/")
            return
            
        # Try to launch Logic
        for path in found_paths:
            logger.info(f"Trying to launch Logic from: {path}")
            if try_launch_saleae(path):
                logger.info(f"Successfully launched Logic from: {path}")
                break
        else:
            logger.error("Failed to launch Logic from any found path")
            return
            
        # Wait for Logic to initialize
        logger.info("Waiting for Logic to initialize...")
        time.sleep(5)
        
        # Connect to device
        saleae = connect_to_device()
        if not saleae:
            logger.error("Failed to connect to any device")
            return
            
        # Create capture instance
        capture = SaleaeCapture(
            sample_rate=16000000,  # 16MHz
            duration=1.0,  # 1 second
            channels=[0, 1, 2, 3]  # First 4 channels
        )
        capture.saleae = saleae
        
        # Configure capture
        if not capture.configure_capture():
            logger.error("Failed to configure capture")
            return
            
        # Start capture
        if not capture.start_capture():
            logger.error("Failed to start capture")
            return
            
        logger.info("Capture started successfully")
        logger.info("Please stop the capture manually in the Logic UI when done")
        
        # Wait for the capture to complete
        try:
            # Wait for the configured duration plus some buffer
            time.sleep(capture.duration + 1)
            logger.info("Capture duration completed")
            
            # Test export_data2 with the captured file
            capture_file = os.path.join(os.getcwd(), "capture.logicdata")
            if os.path.exists(capture_file):
                logger.info("\nTesting export_data2 functionality...")
                test_export_data2(saleae, capture_file)
            else:
                logger.error(f"Capture file not found: {capture_file}")
                
        except KeyboardInterrupt:
            logger.info("\nCapture interrupted by user")
            try:
                capture.stop_capture()
            except Exception as e:
                logger.warning(f"Failed to stop capture: {str(e)}")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        logger.info("Capture process completed")

if __name__ == "__main__":
    main() 