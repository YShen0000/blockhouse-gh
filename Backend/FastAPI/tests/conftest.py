import pytest
import pandas as pd
from datetime import datetime

@pytest.fixture(scope="function")
def mock_data():
    """Common fixture for mock data"""
    return {
        "success": True,
        "message": "Operation successful",
        "data": {"key": "value"}
    }

@pytest.fixture(scope="function")
def mock_dataframe():
    """Common fixture for DataFrame operations"""
    return pd.DataFrame({
        'column1': [1, 2, 3],
        'column2': ['a', 'b', 'c'],
        'date_column': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
    })

@pytest.fixture(autouse=True)
async def mock_db_operations():
    """Fixture to automatically mock all database operations"""
    # Add your database mocking logic here
    yield
