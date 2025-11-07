"""
Pytest configuration and fixtures for testing.

This file contains shared fixtures and configuration for all tests.
"""

import pytest
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def sample_movie():
    """Sample movie data for testing."""
    return {
        "_id": "507f1f77bcf86cd799439011",
        "title": "Test Movie",
        "year": 2024,
        "plot": "A test movie plot",
        "genres": ["Action", "Drama"],
        "directors": ["Test Director"],
        "cast": ["Actor 1", "Actor 2"],
        "runtime": 120,
        "rated": "PG-13"
    }


@pytest.fixture
def sample_movies():
    """Multiple sample movies for testing."""
    return [
        {
            "_id": "507f1f77bcf86cd799439011",
            "title": "Test Movie 1",
            "year": 2024,
            "plot": "First test movie",
            "genres": ["Action"],
        },
        {
            "_id": "507f1f77bcf86cd799439012",
            "title": "Test Movie 2",
            "year": 2023,
            "plot": "Second test movie",
            "genres": ["Comedy"],
        },
        {
            "_id": "507f1f77bcf86cd799439013",
            "title": "Test Movie 3",
            "year": 2024,
            "plot": "Third test movie",
            "genres": ["Drama"],
        }
    ]


@pytest.fixture
def mock_success_response():
    """Mock success response structure."""
    def _create_response(data, message="Success"):
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": "2024-01-01T00:00:00.000Z"
        }
    return _create_response


@pytest.fixture
def mock_error_response():
    """Mock error response structure."""
    def _create_response(message, code=None, details=None):
        return {
            "success": False,
            "message": message,
            "error": {
                "message": message,
                "code": code,
                "details": details
            },
            "timestamp": "2024-01-01T00:00:00.000Z"
        }
    return _create_response

