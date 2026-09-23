from unittest.mock import Mock
import pandas as pd

def create_mock_file():
    """Create mock file object for testing"""
    mock_file = Mock()
    mock_file.filename = "test.csv"
    mock_file.file = Mock()
    mock_file.file.read = Mock(return_value=b"test content")
    return mock_file

def create_mock_response():
    """Create mock response data"""
    return {
        "status": "success",
        "data": {},
        "message": "Operation completed successfully"
    }

def create_mock_error():
    """Create mock error response"""
    return {
        "status": "error",
        "detail": "Operation failed",
        "error_code": 400
    }
