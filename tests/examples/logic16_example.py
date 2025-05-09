#!/usr/bin/env python3
"""
Saleae Logic 16 Automation Example

This script demonstrates how to use the logic2-automation package with a Logic 16 device
to perform digital signal capture and analysis.
"""

import os
import time
from saleae.automation import Manager, LogicDeviceConfiguration, TimedCaptureMode, CaptureConfiguration, DeviceType

def main():
    # Connect to the Logic 2 software
    print("Connecting to Logic 2 software...")
    with Manager.connect() as manager:
        print("Successfully connected to Logic 2")
        
        # Get a list of connected devices
        devices = manager.get_devices()
        if not devices:
            print("No Logic devices found. Please connect a device and try again.")
            return
            
        # Display connected devices
        print(f"Found {len(devices)} device(s):")
        for i, device in enumerate(devices):
            device_id = f"{device.device_id[:4]}...{device.device_id[-4:]}" if len(device.device_id) > 8 else "****"
            print(f"  {i+1}. {device.device_type} (ID: {device_id})")
            
        # Find Logic 16 device
        logic16_device = None
        for device in devices:
            if device.device_type == DeviceType.LOGIC_16:
                logic16_device = device
                break
                
        if not logic16_device:
            print("Logic 16 device not found. Please connect a Logic 16 device and try again.")
            return
            
        print(f"\nUsing device: {logic16_device.device_type}")
        
        # Configure the device
        device_config = LogicDeviceConfiguration(
            enabled_digital_channels=list(range(16)),  # Enable all 16 digital channels
            digital_sample_rate=16000000,  # 16 MHz (maximum supported rate)
        )
        
        # Configure the capture mode
        capture_config = CaptureConfiguration(
            capture_mode=TimedCaptureMode(duration_seconds=10.0)
        )
        
        # Start the capture
        print(f"\nStarting capture for 10.0 seconds...")
        with manager.start_capture(
            device_id=logic16_device.device_id,
            device_configuration=device_config,
            capture_configuration=capture_config
        ) as capture:
            # Wait for capture to complete
            capture.wait()
            print("\nCapture complete!")
            
            # Create output directory
            output_dir = "logic16_output"
            os.makedirs(output_dir, exist_ok=True)
            
            # Save the capture file
            capture_file = os.path.join(output_dir, "logic16_capture.sal")
            capture.save_capture(capture_file)
            print(f"Capture saved to: {capture_file}")
            
            # Export digital data
            print("Exporting raw data...")
            capture.export_raw_data_csv(
                directory=output_dir,
                digital_channels=device_config.enabled_digital_channels
            )
            print(f"Data exported to: {output_dir}/digital.csv")
            
            print("\nExample completed successfully!")

if __name__ == "__main__":
    main() 