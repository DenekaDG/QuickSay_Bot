# Testing Guide for QuickSay Bot

## Setup

### 1. Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### 2. Set Up Test Environment

Create a test database (optional, tests will work with existing DB):

```bash
createdb test_ai_voice_bot
```

Or set environment variables for test database:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=bot_admin
export DB_PASSWORD=password
export DB_NAME=test_ai_voice_bot
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage Report

```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

This creates an HTML coverage report in `htmlcov/index.html`

### Run Specific Test File

```bash
pytest tests/unit/test_database.py -v
```

### Run Specific Test Class

```bash
pytest tests/unit/test_database.py::TestUserOperations -v
```

### Run Specific Test Function

```bash
pytest tests/unit/test_database.py::TestUserOperations::test_insert_new_user -v
```

### Run Tests with Markers

```bash
# Run only unit tests
pytest -m unit

# Run only database tests
pytest -m db

# Run only fast tests (exclude slow)
pytest -m "not slow"
```

### Run with Verbose Output

```bash
pytest -vv
```

### Run with Print Statements

```bash
pytest -s
```

## Test Structure

```
tests/
├── conftest.py                  # Shared fixtures and configuration
├── unit/
│   ├── __init__.py
│   ├── test_database.py         # Database operations tests
│   ├── test_config.py           # Configuration tests
│   └── test_webhook_security.py # Webhook signature tests
└── integration/
    └── (to be added)
```

## Test Coverage Goals

- **Target:** > 80% code coverage
- **Current:** 0% (baseline)
- **Critical modules:**
  - `db/database.py` - Target: 100%
  - `bot.py` - Target: 80%
  - `payment_service.py` - Target: 90%
  - `webhook_server.py` - Target: 95%

## Continuous Integration

### GitHub Actions (if configured)

Tests automatically run on:

- Push to main branch
- Pull requests

### Pre-commit Hooks

Set up git hooks to run tests before commit:

```bash
# Create .git/hooks/pre-commit
#!/bin/bash
pytest --fail-under=80
```

## Common Issues

### Database Connection Error

**Problem:** `psycopg2.OperationalError: could not connect to server`

**Solution:**

```bash
# Start PostgreSQL (if using local)
pg_ctl start -D /usr/local/var/postgres

# Or use Docker
docker run -d -p 5432:5432 postgres:15
```

### Test Timeout

**Problem:** Tests hang or timeout

**Solution:**

```bash
# Run with timeout
pytest --timeout=30
```

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'config'`

**Solution:**

```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

## Writing New Tests

### Test Template

```python
import pytest

class TestNewFeature:
    """Test description"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup before each test"""
        yield
        # Cleanup after each test
    
    def test_something(self):
        """Test description"""
        # Arrange
        data = {"key": "value"}
        
        # Act
        result = some_function(data)
        
        # Assert
        assert result == expected_value
    
    @pytest.mark.slow
    def test_slow_operation(self):
        """This test runs slowly"""
        pass
    
    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (3, 4),
    ])
    def test_multiple_cases(self, input, expected):
        """Test multiple input cases"""
        assert function(input) == expected
```

### Running Tests During Development

```bash
# Watch for changes and rerun tests
pip install pytest-watch
ptw
```

## Debugging Tests

### Print Debug Information

```python
def test_something(caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    # ... test code ...
    print(caplog.text)
```

### Use pdb Debugger

```python
def test_with_debugger():
    import pdb; pdb.set_trace()
    # Debugger will pause here
```

### Verbose Output

```bash
pytest -vv -s --tb=long
```

## Test Reports

After running tests with coverage:

```bash
# View HTML report
open htmlcov/index.html

# View coverage summary
coverage report

# Generate badge (for README)
coverage-badge -o coverage.svg
```

## Best Practices

1. **Keep tests fast** - Mock external services
2. **Test one thing** - Single assertion per test (usually)
3. **Descriptive names** - `test_user_balance_decreases_after_processing`
4. **Isolate tests** - Use fixtures to setup/teardown
5. **Don't test framework** - Test your code, not aiogram/pytest
6. **Mock external APIs** - Use `pytest-mock` for API calls
7. **Use factories** - For complex test data (factory-boy)

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [pytest-cov](https://github.com/pytest-dev/pytest-cov)
- [pytest-mock](https://github.com/pytest-dev/pytest-mock)
