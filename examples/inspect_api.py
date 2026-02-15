import saleae.automation
import inspect

print("Classes in saleae.automation:")
for name, obj in inspect.getmembers(saleae.automation):
    if inspect.isclass(obj):
        print(f" - {name}")

print("\nChecking Capture Modes:")
if hasattr(saleae.automation, 'DigitalTriggerCaptureMode'):
    print(" - DigitalTriggerCaptureMode FOUND")
    sig = inspect.signature(saleae.automation.DigitalTriggerCaptureMode)
    print(f"   Signature: {sig}")

print("\nChecking Analyzer Methods:")
if hasattr(saleae.automation.Manager, 'add_analyzer'):
    print(" - Manager.add_analyzer FOUND")
elif hasattr(saleae.automation.Capture, 'add_analyzer'):
    print(" - Capture.add_analyzer FOUND")

print("\nChecking Glitch Filter:")
if hasattr(saleae.automation.DigitalChannel, 'glitch_filter_width_seconds'):
    print(" - DigitalChannel.glitch_filter_width_seconds FOUND")
