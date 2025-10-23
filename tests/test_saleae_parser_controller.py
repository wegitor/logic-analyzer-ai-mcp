import pytest
import os
from unittest.mock import Mock, patch, call
from logic_analyzer_mcp.controllers.saleae_parser_controller import SaleaeParserController

# Constants for test files
TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), '..', 'logic2-automation', 'python', 'tests', 'assets')
SMALL_SPI_CAPTURE = os.path.join(TEST_FILES_DIR, 'small_spi_capture.sal')
LARGE_SPI_CAPTURE = os.path.join(TEST_FILES_DIR, 'large_spi_capture.sal')
LARGE_ASYNC_CAPTURE = os.path.join(TEST_FILES_DIR, 'large_async_capture.sal')

@pytest.fixture(autouse=True)
def patch_saleae():
    with patch('src.controllers.saleae_parser_controller.Saleae') as mock:
        yield mock

@pytest.fixture
def mock_mcp():
    """Create a mock MCP instance for testing."""
    return Mock()

@pytest.fixture
def controller(mock_mcp):
    """Create a SaleaeParserController instance with a mock MCP."""
    return SaleaeParserController(mock_mcp)

def test_parse_capture_file_with_logic_launch(controller, mock_mcp, mock_saleae):
    """Test parse_capture_file method when Logic software needs to be launched."""
    # Mock the initial connection failure and subsequent launch
    mock_saleae.return_value.connect.side_effect = [
        Exception("Could not connect to Logic software"),
        None  # Second attempt succeeds after launch
    ]
    
    expected_result = {
        "duration": 0.001,
        "digital_channels": 4,
        "analog_channels": 0
    }
    mock_mcp.parse_capture_file.return_value = expected_result
    
    result = controller.parse_capture_file(capture_file=SMALL_SPI_CAPTURE)
    mock_mcp.parse_capture_file.assert_called_once_with(capture_file=SMALL_SPI_CAPTURE, data=None)
    assert result == expected_result
    
    # Verify that connect was called twice and launch was called once
    assert mock_saleae.return_value.connect.call_count == 2
    mock_saleae.return_value.launch.assert_called_once()

def test_parse_capture_file_with_connection_retry(controller, mock_mcp, mock_saleae):
    """Test parse_capture_file method with connection retry logic."""
    # Mock multiple connection failures before success
    mock_saleae.return_value.connect.side_effect = [
        Exception("Connection timeout"),
        Exception("Connection timeout"),
        None  # Third attempt succeeds
    ]
    
    expected_result = {
        "duration": 0.001,
        "digital_channels": 4,
        "analog_channels": 0
    }
    mock_mcp.parse_capture_file.return_value = expected_result
    
    result = controller.parse_capture_file(capture_file=SMALL_SPI_CAPTURE)
    mock_mcp.parse_capture_file.assert_called_once_with(capture_file=SMALL_SPI_CAPTURE, data=None)
    assert result == expected_result
    
    # Verify that connect was called three times
    assert mock_saleae.return_value.connect.call_count == 3

def test_parse_capture_file_with_connection_error(controller, mock_mcp, mock_saleae):
    """Test parse_capture_file method when connection fails permanently."""
    # Mock permanent connection failure
    mock_saleae.return_value.connect.side_effect = Exception("Connection failed permanently")
    
    with pytest.raises(Exception) as exc_info:
        controller.parse_capture_file(capture_file=SMALL_SPI_CAPTURE)
    
    assert "Connection failed permanently" in str(exc_info.value)
    assert mock_saleae.return_value.connect.call_count > 0

def test_parse_capture_file_with_launch_timeout(controller, mock_mcp, mock_saleae):
    """Test parse_capture_file method when Logic software launch times out."""
    # Mock connection failure and launch timeout
    mock_saleae.return_value.connect.side_effect = Exception("Could not connect to Logic software")
    mock_saleae.return_value.launch.side_effect = Exception("Launch timeout")
    
    with pytest.raises(Exception) as exc_info:
        controller.parse_capture_file(capture_file=SMALL_SPI_CAPTURE)
    
    assert "Launch timeout" in str(exc_info.value)
    mock_saleae.return_value.launch.assert_called_once()

def test_parse_capture_file_with_small_spi(controller, mock_mcp):
    """Test parse_capture_file method with small SPI capture file."""
    expected_result = {
        "duration": 0.001,  # 1ms capture
        "digital_channels": 4,  # Assuming 4 digital channels
        "analog_channels": 0
    }
    mock_mcp.parse_capture_file.return_value = expected_result
    
    result = controller.parse_capture_file(capture_file=SMALL_SPI_CAPTURE)
    mock_mcp.parse_capture_file.assert_called_once_with(capture_file=SMALL_SPI_CAPTURE, data=None)
    assert result == expected_result

def test_parse_capture_file_with_large_spi(controller, mock_mcp):
    """Test parse_capture_file method with large SPI capture file."""
    expected_result = {
        "duration": 0.1,  # 100ms capture
        "digital_channels": 4,
        "analog_channels": 0
    }
    mock_mcp.parse_capture_file.return_value = expected_result
    
    result = controller.parse_capture_file(capture_file=LARGE_SPI_CAPTURE)
    mock_mcp.parse_capture_file.assert_called_once_with(capture_file=LARGE_SPI_CAPTURE, data=None)
    assert result == expected_result

def test_parse_capture_file_with_large_async(controller, mock_mcp):
    """Test parse_capture_file method with large async capture file."""
    expected_result = {
        "duration": 0.1,  # 100ms capture
        "digital_channels": 8,  # Assuming 8 digital channels for async capture
        "analog_channels": 0
    }
    mock_mcp.parse_capture_file.return_value = expected_result
    
    result = controller.parse_capture_file(capture_file=LARGE_ASYNC_CAPTURE)
    mock_mcp.parse_capture_file.assert_called_once_with(capture_file=LARGE_ASYNC_CAPTURE, data=None)
    assert result == expected_result

def test_get_digital_data_with_small_spi(controller, mock_mcp):
    """Test get_digital_data method with small SPI capture file."""
    expected_result = {
        "channel": 0,
        "data": [
            (0.000000, True),   # Start of capture
            (0.000100, False),  # First transition
            (0.000200, True),   # Second transition
            (0.000300, False)   # End of capture
        ]
    }
    mock_mcp.get_digital_data.return_value = expected_result
    
    result = controller.get_digital_data(
        capture_file=SMALL_SPI_CAPTURE,
        channel=0,
        start_time=0.0,
        end_time=0.001
    )
    mock_mcp.get_digital_data.assert_called_once_with(
        capture_file=SMALL_SPI_CAPTURE,
        data=None,
        channel=0,
        start_time=0.0,
        end_time=0.001
    )
    assert result == expected_result

def test_get_digital_data_with_large_spi(controller, mock_mcp):
    """Test get_digital_data method with large SPI capture file."""
    expected_result = {
        "channel": 0,
        "data": [
            (0.000000, True),    # Start of capture
            (0.000100, False),   # First transition
            (0.000200, True),    # Second transition
            (0.000300, False),   # Third transition
            (0.000400, True),    # Fourth transition
            (0.000500, False)    # End of capture
        ]
    }
    mock_mcp.get_digital_data.return_value = expected_result
    
    result = controller.get_digital_data(
        capture_file=LARGE_SPI_CAPTURE,
        channel=0,
        start_time=0.0,
        end_time=0.001
    )
    mock_mcp.get_digital_data.assert_called_once_with(
        capture_file=LARGE_SPI_CAPTURE,
        data=None,
        channel=0,
        start_time=0.0,
        end_time=0.001
    )
    assert result == expected_result

def test_get_digital_data_with_large_async(controller, mock_mcp):
    """Test get_digital_data method with large async capture file."""
    expected_result = {
        "channel": 0,
        "data": [
            (0.000000, True),    # Start of capture
            (0.000100, False),   # First transition
            (0.000200, True),    # Second transition
            (0.000300, False),   # Third transition
            (0.000400, True),    # Fourth transition
            (0.000500, False),   # Fifth transition
            (0.000600, True),    # Sixth transition
            (0.000700, False)    # End of capture
        ]
    }
    mock_mcp.get_digital_data.return_value = expected_result
    
    result = controller.get_digital_data(
        capture_file=LARGE_ASYNC_CAPTURE,
        channel=0,
        start_time=0.0,
        end_time=0.001
    )
    mock_mcp.get_digital_data.assert_called_once_with(
        capture_file=LARGE_ASYNC_CAPTURE,
        data=None,
        channel=0,
        start_time=0.0,
        end_time=0.001
    )
    assert result == expected_result

def test_export_digital_data_with_small_spi(controller, mock_mcp):
    """Test export_digital_data method with small SPI capture file."""
    output_file = "test_output.csv"
    expected_result = {
        "status": "success",
        "output_file": output_file,
        "channels_exported": [0, 1, 2, 3],
        "duration": 0.001
    }
    mock_mcp.export_digital_data.return_value = expected_result
    
    result = controller.export_digital_data(
        output_file=output_file,
        capture_file=SMALL_SPI_CAPTURE,
        channels=[0, 1, 2, 3],
        start_time=0.0,
        end_time=0.001
    )
    mock_mcp.export_digital_data.assert_called_once_with(
        output_file=output_file,
        capture_file=SMALL_SPI_CAPTURE,
        data=None,
        channels=[0, 1, 2, 3],
        start_time=0.0,
        end_time=0.001
    )
    assert result == expected_result

def test_export_digital_data_with_large_spi(controller, mock_mcp):
    """Test export_digital_data method with large SPI capture file."""
    output_file = "test_output.csv"
    expected_result = {
        "status": "success",
        "output_file": output_file,
        "channels_exported": [0, 1, 2, 3],
        "duration": 0.1
    }
    mock_mcp.export_digital_data.return_value = expected_result
    
    result = controller.export_digital_data(
        output_file=output_file,
        capture_file=LARGE_SPI_CAPTURE,
        channels=[0, 1, 2, 3],
        start_time=0.0,
        end_time=0.1
    )
    mock_mcp.export_digital_data.assert_called_once_with(
        output_file=output_file,
        capture_file=LARGE_SPI_CAPTURE,
        data=None,
        channels=[0, 1, 2, 3],
        start_time=0.0,
        end_time=0.1
    )
    assert result == expected_result

def test_export_digital_data_with_large_async(controller, mock_mcp):
    """Test export_digital_data method with large async capture file."""
    output_file = "test_output.csv"
    expected_result = {
        "status": "success",
        "output_file": output_file,
        "channels_exported": [0, 1, 2, 3, 4, 5, 6, 7],
        "duration": 0.1
    }
    mock_mcp.export_digital_data.return_value = expected_result
    
    result = controller.export_digital_data(
        output_file=output_file,
        capture_file=LARGE_ASYNC_CAPTURE,
        channels=[0, 1, 2, 3, 4, 5, 6, 7],
        start_time=0.0,
        end_time=0.1
    )
    mock_mcp.export_digital_data.assert_called_once_with(
        output_file=output_file,
        capture_file=LARGE_ASYNC_CAPTURE,
        data=None,
        channels=[0, 1, 2, 3, 4, 5, 6, 7],
        start_time=0.0,
        end_time=0.1
    )
    assert result == expected_result

def test_get_sample_rate_with_small_spi(controller, mock_mcp):
    """Test get_sample_rate method with small SPI capture file."""
    expected_result = {
        "channel": 0,
        "sample_rate": 1000000.0  # 1MHz sample rate
    }
    mock_mcp.get_sample_rate.return_value = expected_result
    
    result = controller.get_sample_rate(
        capture_file=SMALL_SPI_CAPTURE,
        channel=0
    )
    mock_mcp.get_sample_rate.assert_called_once_with(
        capture_file=SMALL_SPI_CAPTURE,
        sample_rate=None,
        channel=0
    )
    assert result == expected_result

def test_get_sample_rate_with_large_spi(controller, mock_mcp):
    """Test get_sample_rate method with large SPI capture file."""
    expected_result = {
        "channel": 0,
        "sample_rate": 1000000.0  # 1MHz sample rate
    }
    mock_mcp.get_sample_rate.return_value = expected_result
    
    result = controller.get_sample_rate(
        capture_file=LARGE_SPI_CAPTURE,
        channel=0
    )
    mock_mcp.get_sample_rate.assert_called_once_with(
        capture_file=LARGE_SPI_CAPTURE,
        sample_rate=None,
        channel=0
    )
    assert result == expected_result

def test_get_sample_rate_with_large_async(controller, mock_mcp):
    """Test get_sample_rate method with large async capture file."""
    expected_result = {
        "channel": 0,
        "sample_rate": 1000000.0  # 1MHz sample rate
    }
    mock_mcp.get_sample_rate.return_value = expected_result
    
    result = controller.get_sample_rate(
        capture_file=LARGE_ASYNC_CAPTURE,
        channel=0
    )
    mock_mcp.get_sample_rate.assert_called_once_with(
        capture_file=LARGE_ASYNC_CAPTURE,
        sample_rate=None,
        channel=0
    )
    assert result == expected_result

def test_parse_capture_file_with_direct_data(controller, mock_mcp):
    """Test parse_capture_file method with direct data input."""
    test_data = {
        "duration": 0.001,
        "digital_channels": 4,
        "analog_channels": 0,
        "sample_rate": 1000000.0
    }
    mock_mcp.parse_capture_file.return_value = test_data
    
    result = controller.parse_capture_file(data=test_data)
    mock_mcp.parse_capture_file.assert_called_once_with(capture_file=None, data=test_data)
    assert result == test_data

def test_get_digital_data_with_direct_data(controller, mock_mcp):
    """Test get_digital_data method with direct data input."""
    test_data = [
        {"time": 0.000000, "value": True},
        {"time": 0.000100, "value": False},
        {"time": 0.000200, "value": True},
        {"time": 0.000300, "value": False}
    ]
    expected_result = {
        "channel": 0,
        "data": [(0.000000, True), (0.000100, False), (0.000200, True), (0.000300, False)]
    }
    mock_mcp.get_digital_data.return_value = expected_result
    
    result = controller.get_digital_data(
        data=test_data,
        channel=0,
        start_time=0.0,
        end_time=0.001
    )
    mock_mcp.get_digital_data.assert_called_once_with(
        capture_file=None,
        data=test_data,
        channel=0,
        start_time=0.0,
        end_time=0.001
    )
    assert result == expected_result

def test_get_analog_data(controller, mock_mcp):
    """Test get_analog_data method."""
    expected_result = {"channel": 0, "data": [(0.0, 3.3), (0.5, 0.0)]}
    mock_mcp.get_analog_data.return_value = expected_result
    
    result = controller.get_analog_data(channel=0, start_time=0.0, end_time=1.0)
    mock_mcp.get_analog_data.assert_called_once_with(
        capture_file=None,
        data=None,
        channel=0,
        start_time=0.0,
        end_time=1.0
    )
    assert result == expected_result

def test_export_analog_data(controller, mock_mcp):
    """Test export_analog_data method."""
    expected_result = {"status": "success", "output_file": "test_output.csv"}
    mock_mcp.export_analog_data.return_value = expected_result
    
    result = controller.export_analog_data(
        output_file="test_output.csv",
        channels=[0, 1],
        start_time=0.0,
        end_time=1.0
    )
    mock_mcp.export_analog_data.assert_called_once_with(
        output_file="test_output.csv",
        capture_file=None,
        data=None,
        channels=[0, 1],
        start_time=0.0,
        end_time=1.0
    )
    assert result == expected_result 