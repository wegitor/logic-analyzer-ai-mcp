import os
import sys
import pytest
from pathlib import Path

# Get the absolute path to the project root directory
project_root = Path(__file__).parent.parent.absolute()

# Add the project root to the Python path
sys.path.insert(0, str(project_root))

# Add the src directory to the Python path
sys.path.insert(0, str(project_root / "src"))

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment."""
    # Add any test setup here
    yield
    # Add any test cleanup here

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root) 