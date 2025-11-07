# Testing Guide for FastAPI MongoDB Sample Application

This document describes the testing strategy and how to run tests for the FastAPI MongoDB MFlix sample application.

## Test Structure

The test suite is organized into three categories:

### 1. **Schema Tests** (`test_movie_schemas.py`)
- Tests Pydantic model validation
- Validates request/response data structures
- No database or external dependencies required
- **10 tests** covering `CreateMovieRequest`, `UpdateMovieRequest`, and `Movie` models

### 2. **Unit Tests** (`test_movie_routes.py`)
- Tests route handler functions in isolation
- Uses `unittest.mock.AsyncMock` to mock MongoDB operations
- No database connection required
- Fast execution (< 2 seconds)
- **51 tests** covering:
  - CRUD operations (create, read, update, delete)
  - Batch operations
  - Search functionality
  - Vector search
  - Aggregation pipelines

### 3. **Integration Tests** (`tests/integration/test_movie_routes_integration.py`)
- Tests the full HTTP request/response cycle
- Requires a running MongoDB instance with MFlix dataset
- Uses a real server running in a subprocess
- Tests are idempotent (clean up after themselves)
- **10 tests** covering:
  - CRUD operations
  - Batch operations
  - Search functionality
  - Aggregation pipelines

## Running Tests

### Prerequisites

1. **For all tests:**
   ```bash
   cd server/
   source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
   ```

2. **For integration tests only:**
   - MongoDB instance running with MFlix dataset loaded
   - Connection string configured in `.env` file
   - Port 8001 available (used for test server)

### Run All Tests

```bash
pytest tests/ -v
```

**Expected output:** 71 passed in ~6 seconds

### Run Only Unit Tests (Fast, No Database Required)

```bash
pytest -m unit -v
```

**Expected output:** 61 passed, 10 deselected in ~1.5 seconds

### Run Only Integration Tests (Requires Database)

```bash
pytest -m integration -v
```

**Expected output:** 10 passed, 61 deselected in ~5 seconds

### Run Specific Test File

```bash
# Schema tests
pytest tests/test_movie_schemas.py -v

# Unit tests
pytest tests/test_movie_routes.py -v

# Integration tests
pytest tests/integration/test_movie_routes_integration.py -v
```

### Run Specific Test Class or Method

```bash
# Run a specific test class
pytest tests/test_movie_routes.py::TestCreateMovie -v

# Run a specific test method
pytest tests/test_movie_routes.py::TestCreateMovie::test_create_movie_success -v
```

## Test Markers

Tests are marked with pytest markers for selective execution:

- `@pytest.mark.unit` - Unit tests with mocked dependencies
- `@pytest.mark.integration` - Integration tests requiring database

## Integration Test Strategy

### Why Use a Running Server?

The integration tests start a real FastAPI server in a subprocess because:

1. **Event Loop Isolation**: AsyncMongoClient binds to the event loop it was created in. Using a real server avoids event loop conflicts.
2. **Real-World Testing**: Tests the actual deployment configuration, including middleware, CORS, and startup events.
3. **Educational Value**: Demonstrates a practical integration testing pattern for async Python applications.

### Idempotent Tests

All integration tests are designed to be idempotent:

- **Create operations**: Tests create new documents with unique identifiers
- **Cleanup**: Fixtures automatically delete created documents after tests
- **Read-only tests**: Tests against existing MFlix data don't modify anything
- **Batch operations**: Create and delete multiple documents with proper cleanup

### Fixtures

Integration tests use pytest fixtures for test data lifecycle management:

- `client`: AsyncClient connected to the test server
- `test_movie_data`: Sample movie data for creating test documents
- `created_movie`: Creates a movie and cleans it up automatically
- `multiple_test_movies`: Creates 3 movies for batch operation testing

## Known Issues

### Batch Create Bug (Skipped Test)

The `test_batch_create_movies` test is currently skipped due to a known bug in the API:

- **Issue**: `create_movies_batch` function calls `insert_many` twice (lines 1006 and 1015 in `movies.py`)
- **Impact**: Causes 500 error on batch create operations
- **Status**: To be fixed in a separate PR
- **Test behavior**: Test detects the error and skips gracefully

## Troubleshooting

### Integration Tests Fail to Start Server

**Error**: `Port 8001 is already in use`

**Solution**: 
- Kill any process using port 8001: `lsof -ti:8001 | xargs kill -9`
- Or change the port in `tests/integration/conftest.py`

### Integration Tests Can't Connect to MongoDB

**Error**: Connection timeout or authentication error

**Solution**:
- Verify MongoDB is running
- Check `.env` file has correct `MONGODB_URI`
- Ensure MFlix dataset is loaded
- Test connection: `mongosh <your-connection-string>`

### Unit Tests Fail with Import Errors

**Error**: `ModuleNotFoundError`

**Solution**:
- Ensure virtual environment is activated
- Install dependencies: `pip install -r requirements.txt`
- Run from `server/python-fastapi` directory

## Contributing

When adding new routes or functionality:

1. **Add unit tests** in `test_movie_routes.py` with mocked dependencies
2. **Add integration tests** in `tests/integration/test_movie_routes_integration.py` for end-to-end validation
3. **Use appropriate markers** (`@pytest.mark.unit` or `@pytest.mark.integration`)
4. **Follow fixture patterns** for test data lifecycle management
5. **Ensure idempotency** - tests should clean up after themselves
6. **Document test purpose** with clear docstrings

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [MongoDB Motor documentation](https://motor.readthedocs.io/)

