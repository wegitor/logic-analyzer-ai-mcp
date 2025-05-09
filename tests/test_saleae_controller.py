import os
import pytest
from unittest.mock import Mock, patch, mock_open, ANY
from src.controllers.saleae_controller import SaleaeController

@pytest.fixture
def mock_saleae():
    """Create a mock Saleae instance."""
    mock = Mock()
    mock.is_processing_complete.return_value = True
    mock.get_active_channels.return_value = ([0, 1], [0])  # Digital and analog channels
    return mock

@pytest.fixture
def saleae_controller(mock_saleae):
    """Create a SaleaeController instance with mocked Saleae."""
    with patch('src.controllers.saleae_controller.Saleae', return_value=mock_saleae):
        controller = SaleaeController()
        controller.saleae = mock_saleae
        return controller

@pytest.fixture
def sample_sal_file(tmp_path):
    """Create a sample .sal file for testing."""
    sal_file = tmp_path / 'test.sal'
    with open(sal_file, 'w') as f:
        f.write('test data')
    return str(sal_file)

@pytest.fixture
def temp_logicdata_file(tmp_path):
    """Create a temporary .logicdata file path."""
    return str(tmp_path / 'test_output.logicdata')

def test_convert_sal_to_logicdata(saleae_controller, sample_sal_file, temp_logicdata_file, mock_saleae):
    """Test converting .sal file to .logicdata format."""
    # Create a mock file handle
    mock_file_handle = mock_open()
    
    # Track which files should exist
    existing_files = {sample_sal_file}
    
    def mock_exists(path):
        """Mock os.path.exists to return True for existing files."""
        return path in existing_files
    
    # Mock file operations
    with patch('builtins.open', mock_file_handle) as mock_file, \
         patch('os.path.exists', side_effect=mock_exists), \
         patch('os.path.getsize', return_value=100), \
         patch('os.makedirs', return_value=None):
        
        # Add the output file to existing files after export
        def mock_export(*args, **kwargs):
            existing_files.add(temp_logicdata_file)
            # Create the output file
            with open(temp_logicdata_file, 'w') as f:
                f.write('mock logicdata content')
            return None
        
        mock_saleae.export_data2.side_effect = mock_export
        
        # Test the conversion
        result = saleae_controller._convert_sal_to_logicdata(sample_sal_file, temp_logicdata_file)
        
        # Verify the result
        assert result is True, "Conversion should return True on success"
        
        # Verify API calls
        mock_saleae.close_all_tabs.assert_called_once()
        mock_saleae.load_from_file.assert_called_once_with(ANY)  # Use ANY to ignore path separator differences
        mock_saleae.get_active_channels.assert_called_once()
        mock_saleae.export_data2.assert_called_once_with(
            ANY,  # Use ANY to ignore path separator differences
            digital_channels=[0, 1],
            analog_channels=[0],
            format='logicdata'
        )

def test_convert_sal_to_logicdata_invalid_file(saleae_controller, tmp_path):
    """Test converting an invalid .sal file."""
    # Create a non-existent file path
    invalid_sal_file = str(tmp_path / 'nonexistent.sal')
    temp_logicdata_file = str(tmp_path / 'test_output.logicdata')
    
    # Mock file operations
    with patch('os.path.exists', return_value=False):
        # Test the conversion
        result = saleae_controller._convert_sal_to_logicdata(invalid_sal_file, temp_logicdata_file)
        
        # Verify the result
        assert result is False, "Conversion should return False for invalid file"

def test_convert_sal_to_logicdata_empty_file(saleae_controller, tmp_path):
    """Test converting an empty .sal file."""
    # Create an empty .sal file
    empty_sal_file = str(tmp_path / 'empty.sal')
    with open(empty_sal_file, 'w') as f:
        pass
    
    temp_logicdata_file = str(tmp_path / 'test_output.logicdata')
    
    def mock_exists(path):
        """Mock os.path.exists to return True only for the empty file."""
        return path == empty_sal_file
    
    # Mock file operations
    with patch('os.path.exists', side_effect=mock_exists), \
         patch('os.path.getsize', return_value=0):
        # Test the conversion
        result = saleae_controller._convert_sal_to_logicdata(empty_sal_file, temp_logicdata_file)
        
        # Verify the result
        assert result is False, "Conversion should return False for empty file"

def test_convert_sal_to_logicdata_permission_error(saleae_controller, tmp_path):
    """Test converting a .sal file with permission issues."""
    # Create a .sal file with no read permissions
    no_permission_file = str(tmp_path / 'no_permission.sal')
    with open(no_permission_file, 'w') as f:
        f.write('test data')
    os.chmod(no_permission_file, 0o000)  # Remove all permissions
    
    temp_logicdata_file = str(tmp_path / 'test_output.logicdata')
    
    try:
        # Mock file operations
        with patch('os.access', return_value=False):
            # Test the conversion
            result = saleae_controller._convert_sal_to_logicdata(no_permission_file, temp_logicdata_file)
            
            # Verify the result
            assert result is False, "Conversion should return False for file with no permissions"
    finally:
        # Restore permissions to allow cleanup
        os.chmod(no_permission_file, 0o666)

def test_convert_sal_to_logicdata_api_error(saleae_controller, sample_sal_file, temp_logicdata_file, mock_saleae):
    """Test handling of API errors during conversion."""
    # Make load_from_file raise an error
    mock_saleae.load_from_file.side_effect = Exception("API Error")
    
    def mock_exists(path):
        """Mock os.path.exists to return True only for the input file."""
        return path == sample_sal_file
    
    # Mock file operations
    with patch('os.path.exists', side_effect=mock_exists), \
         patch('os.path.getsize', return_value=100):
        # Test the conversion
        result = saleae_controller._convert_sal_to_logicdata(sample_sal_file, temp_logicdata_file)
        
        # Verify the result
        assert result is False, "Conversion should return False on API error" 