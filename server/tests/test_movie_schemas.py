"""
Unit Tests for Movie Routes

These tests verify basic API validation and structure.
Following the pattern from PR #21 Express tests - simple validation tests.

Note: These are basic validation tests only. Full integration tests
would require a test database or mocking strategy that handles
AsyncMongoClient event loop binding issues.
"""

import pytest
from pydantic import ValidationError
from src.models.models import CreateMovieRequest, UpdateMovieRequest


# Test constants
TEST_MOVIE_ID = "507f1f77bcf86cd799439011"
INVALID_MOVIE_ID = "invalid-id"


@pytest.mark.unit
class TestMovieCreateValidation:
    """Tests for CreateMovieRequest model validation."""

    def test_create_movie_with_valid_data(self):
        """Should accept valid movie data."""
        movie_data = {
            "title": "Test Movie",
            "year": 2024,
            "plot": "A test movie plot",
            "genres": ["Action", "Drama"],
            "runtime": 120
        }

        movie = CreateMovieRequest(**movie_data)
        assert movie.title == "Test Movie"
        assert movie.year == 2024
        assert movie.plot == "A test movie plot"

    def test_create_movie_missing_required_field(self):
        """Should raise ValidationError when title is missing."""
        movie_data = {
            "year": 2024,
            "plot": "A movie without title"
        }

        with pytest.raises(ValidationError) as exc_info:
            CreateMovieRequest(**movie_data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("title",) for error in errors)

    def test_create_movie_invalid_year_type(self):
        """Should raise ValidationError when year is not an integer."""
        movie_data = {
            "title": "Test Movie",
            "year": "not-a-number"
        }

        with pytest.raises(ValidationError) as exc_info:
            CreateMovieRequest(**movie_data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("year",) for error in errors)

    def test_create_movie_with_optional_fields(self):
        """Should accept movie with only required fields."""
        movie_data = {
            "title": "Minimal Movie"
        }

        movie = CreateMovieRequest(**movie_data)
        assert movie.title == "Minimal Movie"
        assert movie.year is None
        assert movie.plot is None


@pytest.mark.unit
class TestMovieUpdateValidation:
    """Tests for UpdateMovieRequest model validation."""

    def test_update_movie_with_valid_data(self):
        """Should accept valid update data."""
        update_data = {
            "title": "Updated Title",
            "year": 2025
        }

        movie_update = UpdateMovieRequest(**update_data)
        assert movie_update.title == "Updated Title"
        assert movie_update.year == 2025

    def test_update_movie_with_partial_data(self):
        """Should accept partial update data."""
        update_data = {
            "title": "Only Title Updated"
        }

        movie_update = UpdateMovieRequest(**update_data)
        assert movie_update.title == "Only Title Updated"
        assert movie_update.year is None

    def test_update_movie_empty_data(self):
        """Should accept empty update (all fields optional)."""
        update_data = {}

        movie_update = UpdateMovieRequest(**update_data)
        assert movie_update.title is None
        assert movie_update.year is None


@pytest.mark.unit
class TestMovieDataStructure:
    """Tests for movie data structure and types."""

    def test_movie_with_all_fields(self):
        """Should handle movie with all possible fields."""
        movie_data = {
            "title": "Complete Movie",
            "year": 2024,
            "plot": "Full plot",
            "fullplot": "Extended plot description",
            "genres": ["Action", "Drama", "Thriller"],
            "runtime": 142,
            "cast": ["Actor 1", "Actor 2", "Actor 3"],
            "directors": ["Director 1"],
            "writers": ["Writer 1", "Writer 2"],
            "languages": ["English", "Spanish"],
            "rated": "PG-13",
            "countries": ["USA"]
        }

        movie = CreateMovieRequest(**movie_data)
        assert movie.title == "Complete Movie"
        assert len(movie.genres) == 3
        assert len(movie.cast) == 3

    def test_movie_genres_as_list(self):
        """Should accept genres as a list."""
        movie_data = {
            "title": "Genre Test",
            "genres": ["Sci-Fi", "Adventure"]
        }

        movie = CreateMovieRequest(**movie_data)
        assert isinstance(movie.genres, list)
        assert "Sci-Fi" in movie.genres

    def test_movie_with_numeric_fields(self):
        """Should handle numeric fields correctly."""
        movie_data = {
            "title": "Numeric Test",
            "year": 2024,
            "runtime": 120
        }

        movie = CreateMovieRequest(**movie_data)
        assert isinstance(movie.year, int)
        assert isinstance(movie.runtime, int)
