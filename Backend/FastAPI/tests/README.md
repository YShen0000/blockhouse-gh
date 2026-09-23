# Test Structure

Tests are organized by API families (S3, Graph, Files, Report, Recommendation) with separate testing for routes and services.

## Directory Structure
```
tests/
├── routers/                     
│   ├── test_s3_routes.py       
│   ├── test_graph_routes.py    
│   ├── test_file_routes.py     
│   ├── test_report_routes.py   
│   └── test_recommendation_routes.py
├── services/                    
│   ├── test_s3_services.py     
│   ├── test_graph_services.py  
│   ├── test_file_services.py   
│   ├── test_report_services.py 
│   └── test_recommendation_services.py
│
├── utils/ # Utility function tests
├── conftest.py # Common test fixtures
├── fixtures.py # Test data fixtures
└── test_main.py # Main application tests
```

## Running Tests

### Test Specific Service
```
pytest tests/services/test_service_file_name.py
```

### Test Specific Route
```
pytest tests/routers/test_route_file_name.py
```

### Test Coverage
```
pytest --cov=app tests/
```

## Testing Framework

### Core Libraries (Present in requirements.txt)
- `pytest`: Test runner and framework
- `pytest-asyncio`: Async test support
- `pytest-mock`: Mocking utilities
- `pytest-cov`: Coverage reporting
- `httpx`: HTTP client for testing
- `mypy`: Type checking

---

### Key Features
- Isolated test environments for routes and services
- Comprehensive mocking of external dependencies
- Async/await support for FastAPI endpoints
- Proper error handling validation

---

### Best Practices
1. Route tests focus on:
   - Request validation
   - Response structure
   - Status codes
   - Error handling

2. Service tests focus on:
   - Business logic
   - Data processing
   - Error scenarios
   - Edge cases

---
```
Each test suite maintains isolation between route testing and service testing, ensuring changes in one layer don't affect tests in another.
