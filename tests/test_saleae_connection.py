import os
import sys
import time
import logging
from saleae import Saleae
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
        os.path.expandvars(r"%ProgramFiles%\Saleae\Logic\Logic.exe"),
        os.path.expandvars(r"%ProgramFiles%\Logic\Logic.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Saleae\Logic\Logic.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Saleae\Logic\Logic.exe")
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
    
    return found_paths

def try_launch_saleae(path):
    """Try to launch Saleae Logic using different methods."""
    logger.info(f"\nAttempting to launch Saleae Logic from: {path}")
    
    # Method 1: Using subprocess
    try:
        logger.info("Method 1: Using subprocess.Popen...")
        process = subprocess.Popen([path])
        logger.info("✓ Process started")
        time.sleep(2)  # Wait for startup
        return True
    except Exception as e:
        logger.error(f"✗ Subprocess launch failed: {str(e)}")
    
    # Method 2: Using Saleae API
    try:
        logger.info("Method 2: Using Saleae API...")
        saleae = Saleae()
        saleae.launch()
        logger.info("✓ API launch attempted")
        time.sleep(2)  # Wait for startup
        return True
    except Exception as e:
        logger.error(f"✗ API launch failed: {str(e)}")
    
    return False

def test_capture(saleae):
    """Test capturing data from Saleae Logic."""
    logger.info("\nTesting data capture...")
    
    try:
        # Get connected devices
        devices = saleae.get_connected_devices()
        if not devices:
            logger.error("No devices connected for capture test")
            return False
            
        # Get the first connected device
        device = devices[0]
        logger.info(f"Using device: {device}")
        
        # Configure capture settings with more conservative values
        logger.info("Configuring capture settings...")
        try:
            # First try to get current settings
            current_rate = saleae.get_sample_rate()
            logger.info(f"Current sample rate: {current_rate}")
            
            # Set more conservative capture settings
            saleae.set_active_channels([0])  # Enable only first channel initially
            saleae.set_sample_rate(1000000)  # Start with 1MHz sample rate
            saleae.set_capture_seconds(0.5)  # Shorter capture duration
            
            # Verify settings were applied
            new_rate = saleae.get_sample_rate()
            if new_rate != 1000000:
                logger.warning(f"Sample rate not set correctly. Expected 1000000, got {new_rate}")
                # Try a lower rate
                saleae.set_sample_rate(500000)
                logger.info("Retrying with 500kHz sample rate")
            
            # Start capture with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"Starting capture (attempt {attempt + 1}/{max_retries})...")
                    saleae.start_capture()
                    
                    # Wait for capture to complete with timeout
                    timeout = 10  # seconds
                    start_time = time.time()
                    while not saleae.is_processing_complete():
                        if time.time() - start_time > timeout:
                            raise TimeoutError("Capture timeout exceeded")
                        time.sleep(0.1)
                    
                    logger.info("✓ Capture completed successfully")
                    return True
                    
                except Exception as capture_error:
                    logger.error(f"Capture attempt {attempt + 1} failed: {str(capture_error)}")
                    if attempt < max_retries - 1:
                        logger.info("Waiting before retry...")
                        time.sleep(2)  # Wait before retry
                    else:
                        raise  # Re-raise the last error if all retries failed
            
        except Exception as config_error:
            logger.error(f"Failed to configure capture settings: {str(config_error)}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Capture test failed: {str(e)}")
        return False

def verify_saleae_connection(saleae, max_retries=3):
    """Verify that Saleae connection is working properly."""
    logger.info("\nVerifying Saleae connection...")
    
    for attempt in range(max_retries):
        try:
            # Try to get device info
            devices = saleae.get_connected_devices()
            if devices:
                logger.info("✓ Connection verified - devices found")
                return True
            else:
                logger.warning(f"Connection attempt {attempt + 1}: No devices found")
        except Exception as e:
            logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
        
        if attempt < max_retries - 1:
            logger.info("Waiting before retry...")
            time.sleep(2)
    
    return False

def test_start_capture(saleae):
    """Test if capture can be started properly."""
    logger.info("\nTesting capture start functionality...")
    
    try:
        # First verify connection is still good
        if not verify_saleae_connection(saleae):
            logger.error("Connection verification failed before capture test")
            return False
            
        # Configure minimal capture settings
        logger.info("Configuring minimal capture settings...")
        try:
            saleae.set_active_channels([0])  # Single channel
            saleae.set_sample_rate(1000000)  # 1MHz
            saleae.set_capture_seconds(0.1)  # Very short capture
        except Exception as e:
            logger.error(f"Failed to configure capture settings: {str(e)}")
            return False
        
        # Try to start capture with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to start capture (attempt {attempt + 1}/{max_retries})...")
                saleae.start_capture()
                
                # Wait a moment for capture to start
                time.sleep(0.5)
                
                # Check if capture is running
                if saleae.is_capture_running():
                    logger.info("✓ Capture started successfully")
                    # Stop the capture immediately
                    saleae.stop_capture()
                    logger.info("Capture stopped")
                    return True
                else:
                    logger.warning(f"Capture not running after start (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.error(f"Capture start attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                logger.info("Waiting before retry...")
                time.sleep(2)
        
        logger.error("All capture start attempts failed")
        return False
            
    except Exception as e:
        logger.error(f"✗ Start capture test failed: {str(e)}")
        return False

def test_saleae_connection():
    """Test connection to Saleae Logic."""
    logger.info("\nTesting Saleae Logic connection...")
    
    # Check installation paths
    found_paths = check_saleae_paths()
    
    if not found_paths:
        logger.error("\nNo Saleae Logic installation found!")
        logger.info("Please install Saleae Logic from: https://www.saleae.com/downloads/")
        return False
    
    # Try to launch from each found path
    for path in found_paths:
        if try_launch_saleae(path):
            # Try to create Saleae instance
            try:
                logger.info("\nAttempting to create Saleae instance...")
                saleae = Saleae()
                
                # Wait for Logic to fully start
                logger.info("Waiting for Logic to initialize...")
                time.sleep(5)
                
                # Verify connection
                if not verify_saleae_connection(saleae):
                    logger.error("Failed to verify connection to Logic")
                    continue
                
                devices = saleae.get_connected_devices()
                logger.info("✓ Successfully connected to Saleae Logic!")
                if devices:
                    logger.info(f"Found {len(devices)} connected devices:")
                    for device in devices:
                        logger.info(f"  - {device}")
                    
                    # First test if we can start a capture
                    if not test_start_capture(saleae):
                        logger.error("✗ Start capture test failed")
                        return False
                    
                    # Then test full capture functionality
                    if test_capture(saleae):
                        logger.info("✓ All tests completed successfully!")
                        return True
                    else:
                        logger.error("✗ Capture test failed")
                        return False
                else:
                    logger.info("No devices connected")
                return True
            except Exception as e:
                logger.error(f"✗ Failed to create Saleae instance: {str(e)}")
    
    logger.error("\nFailed to connect to Saleae Logic!")
    return False

if __name__ == "__main__":
    logger.info("Starting Saleae Logic connection test...")
    success = test_saleae_connection()
    sys.exit(0 if success else 1) 