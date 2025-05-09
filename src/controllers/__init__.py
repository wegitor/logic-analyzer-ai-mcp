"""
Controllers package for Saleae Logic Usage.

This package contains the Logic2AutomationController for Logic 2 device and capture management:
- Logic2AutomationController: Device configuration, capture management, and device discovery
"""

# Import controllers so they can be imported from the controllers package
from .logic2_automation_controller import Logic2AutomationController

# Note: The TemplateController class has been moved to template_controller.py to avoid import issues

__all__ = ['Logic2AutomationController']
