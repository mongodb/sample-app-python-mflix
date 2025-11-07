"""
Shared fixtures for integration tests.

This module demonstrates MongoDB data lifecycle management patterns
for integration testing with FastAPI and MongoDB.

These integration tests use a real running server to avoid event loop
issues with AsyncMongoClient. This approach:
- Tests the actual deployment configuration
- Avoids event loop binding issues
- Demonstrates real-world integration testing patterns
"""

import uuid
import time
import subprocess
import sys
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient
import socket


def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


@pytest.fixture(scope="session")
def server():
    """
    Start the FastAPI server in a subprocess for integration testing.

    This fixture demonstrates:
    - Starting a real server for integration tests
    - Proper cleanup of server process
    - Waiting for server to be ready
    - Using a test-specific port

    The server runs for the entire test session and is shared across all tests.
    """
    # Use a different port for testing to avoid conflicts
    test_port = 8001

    # Check if port is already in use
    if is_port_in_use(test_port):
        pytest.skip(f"Port {test_port} is already in use. Cannot start test server.")

    # Get the absolute path to the server/python-fastapi directory
    # Tests are in server/python-fastapi/tests/integration, so go up two levels
    test_dir = os.path.dirname(os.path.abspath(__file__))
    server_python_dir = os.path.abspath(os.path.join(test_dir, "..", ".."))

    # Start the server process
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(test_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=server_python_dir
    )

    # Wait for server to be ready (max 10 seconds)
    max_wait = 10
    start_time = time.time()
    while time.time() - start_time < max_wait:
        if is_port_in_use(test_port):
            # Server is ready
            time.sleep(0.5)  # Give it a bit more time to fully initialize
            break
        time.sleep(0.1)
    else:
        # Server didn't start in time
        process.kill()
        pytest.fail(f"Server failed to start within {max_wait} seconds")

    yield f"http://127.0.0.1:{test_port}"

    # Cleanup: Stop the server
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest_asyncio.fixture
async def client(server):
    """
    Create an AsyncClient that connects to the running test server.

    This client makes real HTTP requests to the server running in a subprocess,
    testing the full request/response cycle including:
    - Request validation
    - Route handlers
    - Database operations
    - Response serialization
    - Middleware
    - CORS

    This approach avoids event loop issues with AsyncMongoClient.
    """
    async with AsyncClient(base_url=server, timeout=30.0) as ac:
        yield ac


@pytest.fixture
def test_movie_data():
    """
    Generate unique test movie data.
    
    Uses UUID to ensure uniqueness and avoid conflicts with:
    - Existing MFlix data
    - Other concurrent tests
    - Previous test runs
    
    Returns minimal required fields for a valid movie document.
    """
    unique_id = str(uuid.uuid4())[:8]
    return {
        "title": f"Integration Test Movie {unique_id}",
        "year": 2024,
        "plot": f"This is a test movie created during integration testing. ID: {unique_id}",
        "genres": ["Test", "Integration"],
        "runtime": 120,
        "cast": ["Test Actor 1", "Test Actor 2"],
        "directors": ["Test Director"],
        "rated": "PG-13"
    }


@pytest_asyncio.fixture
async def created_movie(client, test_movie_data):
    """
    Create a test movie and automatically clean it up after the test.

    This fixture demonstrates the create -> test -> cleanup pattern:
    1. POST request creates a new movie
    2. Yield the movie ID to the test
    3. DELETE request removes the movie (runs even if test fails)

    Usage:
        async def test_something(created_movie):
            # created_movie is the movie ID
            response = await client.get(f"/api/movies/{created_movie}")
            # ... test assertions ...
            # Cleanup happens automatically
    """
    # Setup: Create test movie
    response = await client.post("/api/movies/", json=test_movie_data)
    assert response.status_code in [200, 201], f"Failed to create test movie: {response.text}"

    movie_id = response.json()["data"]["_id"]

    # Provide movie ID to test
    yield movie_id

    # Teardown: Clean up test movie (always runs)
    cleanup_response = await client.delete(f"/api/movies/{movie_id}")
    # Verify cleanup succeeded (helps catch cleanup issues early)
    assert cleanup_response.status_code == 200, f"Failed to clean up test movie {movie_id}"


@pytest_asyncio.fixture
async def multiple_test_movies(client):
    """
    Create multiple test movies for batch operation testing.

    This fixture demonstrates:
    - Creating multiple related test documents
    - Tracking all created IDs for cleanup
    - Cleaning up all documents even if test fails

    Usage:
        async def test_batch_operation(multiple_test_movies):
            # multiple_test_movies is a list of movie IDs
            assert len(multiple_test_movies) == 3
            # ... test batch operations ...
            # All movies cleaned up automatically
    """
    movie_ids = []
    unique_id = str(uuid.uuid4())[:8]

    # Create 3 test movies
    for i in range(3):
        movie_data = {
            "title": f"Batch Test Movie {i} - {unique_id}",
            "year": 2024,
            "plot": f"Batch test movie {i}",
            "genres": ["Test"],
            "runtime": 90
        }
        response = await client.post("/api/movies/", json=movie_data)
        assert response.status_code in [200, 201], f"Failed to create batch test movie {i}"
        movie_ids.append(response.json()["data"]["_id"])

    yield movie_ids

    # Cleanup all test movies
    # Note: Some tests may have already deleted these movies, so we handle that gracefully
    for movie_id in movie_ids:
        cleanup_response = await client.delete(f"/api/movies/{movie_id}")
        # Accept 200 (success) or 500 (movie already deleted)
        if cleanup_response.status_code == 500:
            # Check if it's a "not found" error
            response_data = cleanup_response.json()
            if response_data.get("success") is False and "not found" in response_data.get("error", {}).get("message", "").lower():
                # Movie was already deleted, which is fine
                continue
        assert cleanup_response.status_code == 200, f"Failed to clean up movie {movie_id}"

