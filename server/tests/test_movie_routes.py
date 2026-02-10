"""
Unit Tests for Movie Routes

These tests verify the route handler logic using mocked MongoDB operations.
Tests use unittest.mock.AsyncMock to mock database calls without requiring
an actual database connection or server instance.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from fastapi import HTTPException

from src.models.models import CreateMovieRequest, UpdateMovieRequest
from src.utils.exceptions import VoyageAuthError, VoyageAPIError


# Test constants
TEST_MOVIE_ID = "507f1f77bcf86cd799439011"
INVALID_MOVIE_ID = "invalid-id"


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetMovieById:
    """Tests for GET /api/movies/{id} endpoint."""

    @patch('src.routers.movies.get_collection')
    async def test_get_movie_by_id_success(self, mock_get_collection):
        """Should return movie when valid ID is provided and movie exists."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_movie = {
            "_id": ObjectId(TEST_MOVIE_ID),
            "title": "Test Movie",
            "year": 2024,
            "plot": "A test movie plot"
        }
        mock_collection.find_one.return_value = mock_movie
        mock_get_collection.return_value = mock_collection

        # Import and call the route handler
        from src.routers.movies import get_movie_by_id
        result = await get_movie_by_id(TEST_MOVIE_ID)

        # Assertions
        assert result.success is True
        assert result.data["title"] == "Test Movie"
        assert result.data["_id"] == TEST_MOVIE_ID
        mock_collection.find_one.assert_called_once_with({"_id": ObjectId(TEST_MOVIE_ID)})

    @patch('src.routers.movies.get_collection')
    async def test_get_movie_by_id_not_found(self, mock_get_collection):
        """Should return error when movie does not exist."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None
        mock_get_collection.return_value = mock_collection

        # Import and call the route handler
        from src.routers.movies import get_movie_by_id
        with pytest.raises(HTTPException) as e:
            await get_movie_by_id(TEST_MOVIE_ID)

        # Assertions
        assert e.value.status_code == 404
        assert "no movie found" in str(e.value.detail).lower()

    async def test_get_movie_by_id_invalid_id(self):
        """Should return error when invalid ObjectId format is provided."""
        # Import and call the route handler
        from src.routers.movies import get_movie_by_id
        with pytest.raises(HTTPException) as e:
            await get_movie_by_id(INVALID_MOVIE_ID)

        # Assertions
        assert e.value.status_code == 400
        assert " not a valid" in str(e.value.detail).lower()

    @patch('src.routers.movies.get_collection')
    async def test_get_movie_by_id_database_error(self, mock_get_collection):
        """Should return error when database operation fails."""
        # Setup mock to raise exception
        mock_collection = AsyncMock()
        mock_collection.find_one.side_effect = Exception("Database connection failed")
        mock_get_collection.return_value = mock_collection

        # Import and call the route handler
        from src.routers.movies import get_movie_by_id
        with pytest.raises(HTTPException) as e:
            await get_movie_by_id(TEST_MOVIE_ID)

        # Assertions
        assert e.value.status_code == 500
        assert "error" in str(e.value.detail).lower()


@pytest.mark.unit
@pytest.mark.asyncio
class TestCreateMovie:
    """Tests for POST /api/movies/ endpoint."""

    @patch('src.routers.movies.get_collection')
    async def test_create_movie_success(self, mock_get_collection):
        """Should create movie and return created movie data."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_result = MagicMock()
        mock_result.acknowledged = True
        mock_result.inserted_id = ObjectId(TEST_MOVIE_ID)
        mock_collection.insert_one.return_value = mock_result

        mock_created_movie = {
            "_id": ObjectId(TEST_MOVIE_ID),
            "title": "New Movie",
            "year": 2024,
            "plot": "A new movie"
        }
        mock_collection.find_one.return_value = mock_created_movie
        mock_get_collection.return_value = mock_collection

        # Create request
        from src.routers.movies import create_movie
        movie_request = CreateMovieRequest(
            title="New Movie",
            year=2024,
            plot="A new movie"
        )
        result = await create_movie(movie_request)

        # Assertions
        assert result.success is True
        assert result.data["title"] == "New Movie"
        assert result.data["_id"] == TEST_MOVIE_ID
        mock_collection.insert_one.assert_called_once()

    @patch('src.routers.movies.get_collection')
    async def test_create_movie_database_error(self, mock_get_collection):
        """Should return error when database insert fails."""
        # Setup mock to raise exception
        mock_collection = AsyncMock()
        mock_collection.insert_one.side_effect = Exception("Insert failed")
        mock_get_collection.return_value = mock_collection

        # Create request
        from src.routers.movies import create_movie
        movie_request = CreateMovieRequest(title="New Movie")
        with pytest.raises(HTTPException) as e:
            await create_movie(movie_request)

        # Assertions
        assert e.value.status_code == 500
        assert "error" in str(e.value.detail).lower()


@pytest.mark.unit
@pytest.mark.asyncio
class TestUpdateMovie:
    """Tests for PATCH /api/movies/{id} endpoint."""

    @patch('src.routers.movies.get_collection')
    async def test_update_movie_success(self, mock_get_collection):
        """Should update movie and return updated movie data."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result

        mock_updated_movie = {
            "_id": ObjectId(TEST_MOVIE_ID),
            "title": "Updated Movie",
            "year": 2025,
            "plot": "Updated plot"
        }
        mock_collection.find_one.return_value = mock_updated_movie
        mock_get_collection.return_value = mock_collection

        # Create request
        from src.routers.movies import update_movie
        update_request = UpdateMovieRequest(title="Updated Movie", year=2025)
        result = await update_movie(update_request, TEST_MOVIE_ID)

        # Assertions
        assert result.success is True
        assert result.data["title"] == "Updated Movie"
        mock_collection.update_one.assert_called_once()

    @patch('src.routers.movies.get_collection')
    async def test_update_movie_not_found(self, mock_get_collection):
        """Should return error when movie to update does not exist."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_result = MagicMock()
        mock_result.matched_count = 0
        mock_collection.update_one.return_value = mock_result
        mock_get_collection.return_value = mock_collection

        # Create request
        from src.routers.movies import update_movie
        update_request = UpdateMovieRequest(title="Updated Movie")
        
        with pytest.raises(HTTPException) as e:
            await update_movie(update_request, TEST_MOVIE_ID)
            
            #Assertions
        assert e.value.status_code == 404
        assert "no movie" in str(e.value.detail.lower())

    async def test_update_movie_invalid_id(self):
        """Should return error when invalid ObjectId format is provided."""
        # Create request
        from src.routers.movies import update_movie
        update_request = UpdateMovieRequest(title="Updated Movie")
        
        with pytest.raises(HTTPException) as e:
            await update_movie(update_request, INVALID_MOVIE_ID)

            # Assertions
        assert e.value.status_code == 400
        assert "invalid" in str(e.value.detail.lower())


@pytest.mark.unit
@pytest.mark.asyncio
class TestDeleteMovie:
    """Tests for DELETE /api/movies/{id} endpoint."""

    @patch('src.routers.movies.get_collection')
    async def test_delete_movie_success(self, mock_get_collection):
        """Should delete movie and return success response."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result
        mock_get_collection.return_value = mock_collection

        # Call the route handler
        from src.routers.movies import delete_movie_by_id
        result = await delete_movie_by_id(TEST_MOVIE_ID)

        # Assertions
        assert result.success is True
        assert result.data["deletedCount"] == 1
        mock_collection.delete_one.assert_called_once_with({"_id": ObjectId(TEST_MOVIE_ID)})

    @patch('src.routers.movies.get_collection')
    async def test_delete_movie_not_found(self, mock_get_collection):
        """Should return error when movie to delete does not exist."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_collection.delete_one.return_value = mock_result
        mock_get_collection.return_value = mock_collection

        # Call the route handler
        from src.routers.movies import delete_movie_by_id
        with pytest.raises(HTTPException) as e:
            await delete_movie_by_id(TEST_MOVIE_ID)

            # Assertions
        assert e.value.status_code == 404
        assert "no movie" in str(e.value.detail.lower())

    async def test_delete_movie_invalid_id(self):
        """Should return error when invalid ObjectId format is provided."""
        # Call the route handler
        from src.routers.movies import delete_movie_by_id
        with pytest.raises(HTTPException) as e:
            await delete_movie_by_id(INVALID_MOVIE_ID)
        
        # Assertions
        assert e.value.status_code == 400
        assert "invalid movie id" in str(e.value.detail.lower())

    @patch('src.routers.movies.get_collection')
    async def test_delete_movie_database_error(self, mock_get_collection):
        """Should return error when database operation fails."""
        # Setup mock to raise exception
        mock_collection = AsyncMock()
        mock_collection.delete_one.side_effect = Exception("Delete failed")
        mock_get_collection.return_value = mock_collection

        # Call the route handler
        from src.routers.movies import delete_movie_by_id
        with pytest.raises(HTTPException) as e:
            await delete_movie_by_id(TEST_MOVIE_ID)

            # Assertions
        assert e.value.status_code == 500
        assert "error" in str(e.value.detail.lower())

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetAllMovies:
    """Tests for GET /api/movies/ endpoint."""

    @patch('src.routers.movies.get_collection')
    async def test_get_all_movies_success(self, mock_get_collection):
        """Should return list of movies with default pagination."""
        # Setup mock with proper cursor chaining
        mock_collection = MagicMock()
        mock_cursor = MagicMock()

        # Mock the chaining: find().sort().skip().limit()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor

        # Mock async iteration
        mock_cursor.__aiter__.return_value = iter([
            {"_id": ObjectId(TEST_MOVIE_ID), "title": "Movie 1", "year": 2024},
            {"_id": ObjectId("507f1f77bcf86cd799439012"), "title": "Movie 2", "year": 2023}
        ])

        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        # Call the route handler
        from src.routers.movies import get_all_movies
        result = await get_all_movies()

        # Assertions
        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]["title"] == "Movie 1"
        mock_collection.find.assert_called_once()

    @patch('src.routers.movies.get_collection')
    async def test_get_all_movies_with_filters(self, mock_get_collection):
        """Should filter movies by genre and year."""
        # Setup mock with proper cursor chaining
        mock_collection = MagicMock()
        mock_cursor = MagicMock()

        # Mock the chaining: find().sort().skip().limit()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor

        # Mock async iteration
        mock_cursor.__aiter__.return_value = iter([
            {"_id": ObjectId(TEST_MOVIE_ID), "title": "Action Movie", "year": 2024, "genres": ["Action"]}
        ])

        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        # Call the route handler with filters
        from src.routers.movies import get_all_movies
        result = await get_all_movies(genre="Action", year=2024)

        # Assertions
        assert result.success is True
        assert len(result.data) == 1
        assert "Action" in result.data[0]["genres"]

    @patch('src.routers.movies.get_collection')
    async def test_get_all_movies_empty_result(self, mock_get_collection):
        """Should return empty list when no movies match filters."""
        # Setup mock with proper cursor chaining
        mock_collection = MagicMock()
        mock_cursor = MagicMock()

        # Mock the chaining: find().sort().skip().limit()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor

        # Mock async iteration with empty list
        mock_cursor.__aiter__.return_value = iter([])

        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        # Call the route handler
        from src.routers.movies import get_all_movies
        result = await get_all_movies(year=1800)

        # Assertions
        assert result.success is True
        assert len(result.data) == 0

    @patch('src.routers.movies.get_collection')
    async def test_get_all_movies_database_error(self, mock_get_collection):
        """Should return error when database operation fails."""
        # Setup mock to raise exception - use MagicMock since find() is synchronous
        mock_collection = MagicMock()
        mock_collection.find.side_effect = Exception("Database error")
        mock_get_collection.return_value = mock_collection

        # Call the route handler
        from src.routers.movies import get_all_movies
        with pytest.raises(HTTPException) as e:
            await get_all_movies()

        # Assertions
        assert e.value.status_code == 500
        assert "error" in str(e.value.detail.lower())


@pytest.mark.unit
@pytest.mark.asyncio
class TestBatchOperations:
    """Tests for batch create and delete operations."""

    @patch('src.routers.movies.get_collection')
    async def test_create_movies_batch_success(self, mock_get_collection):
        """Should create multiple movies in batch."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_result = MagicMock()
        mock_result.acknowledged = True
        mock_result.inserted_ids = [
            ObjectId(TEST_MOVIE_ID),
            ObjectId("507f1f77bcf86cd799439012")
        ]
        mock_collection.insert_many.return_value = mock_result
        mock_get_collection.return_value = mock_collection

        # Create request
        from src.routers.movies import create_movies_batch
        movies = [
            CreateMovieRequest(title="Movie 1", year=2024),
            CreateMovieRequest(title="Movie 2", year=2023)
        ]
        result = await create_movies_batch(movies)

        # Assertions
        assert result.success is True
        assert result.data["insertedCount"] == 2
        assert mock_collection.insert_many.call_count == 1

    @patch('src.routers.movies.get_collection')
    async def test_create_movies_batch_empty_list(self, mock_get_collection):
        """Should return error when empty list is provided."""
        mock_get_collection.return_value = AsyncMock()

        # Create request with empty list
        from src.routers.movies import create_movies_batch
        with pytest.raises(HTTPException) as e:
            await create_movies_batch([])

        # Assertions
        assert e.value.status_code == 400
        assert "empty" in str(e.value.detail.lower())

    @patch('src.routers.movies.get_collection')
    async def test_delete_movies_batch_success(self, mock_get_collection):
        """Should delete multiple movies matching filter."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_result = MagicMock()
        mock_result.deleted_count = 3
        mock_collection.delete_many.return_value = mock_result
        mock_get_collection.return_value = mock_collection

        # Create request
        from src.routers.movies import delete_movies_batch
        request_body = {"filter": {"year": 2020}}
        result = await delete_movies_batch(request_body)

        # Assertions
        assert result.success is True
        assert result.data["deletedCount"] == 3
        mock_collection.delete_many.assert_called_once()

    @patch('src.routers.movies.get_collection')
    async def test_delete_movies_batch_missing_filter(self, mock_get_collection):
        """Should return error when filter is missing."""
        mock_get_collection.return_value = AsyncMock()

        # Create request without filter
        from src.routers.movies import delete_movies_batch
        request_body = {}
        with pytest.raises(HTTPException) as e:
            await delete_movies_batch(request_body)

        # Assertions
        assert e.value.status_code == 400
        assert "filter" in e.value.detail.lower()



@pytest.mark.unit
@pytest.mark.asyncio
class TestFindAndDeleteMovie:
    """Tests for DELETE /api/movies/{id}/find-and-delete endpoint."""

    @patch('src.routers.movies.get_collection')
    async def test_find_and_delete_success(self, mock_get_collection):
        """Should find and delete movie in atomic operation."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_deleted_movie = {
            "_id": ObjectId(TEST_MOVIE_ID),
            "title": "Deleted Movie",
            "year": 2024
        }
        mock_collection.find_one_and_delete.return_value = mock_deleted_movie
        mock_get_collection.return_value = mock_collection

        # Call the route handler
        from src.routers.movies import find_and_delete_movie
        result = await find_and_delete_movie(TEST_MOVIE_ID)

        # Assertions
        assert result.success is True
        assert result.data["title"] == "Deleted Movie"
        assert result.data["_id"] == TEST_MOVIE_ID
        mock_collection.find_one_and_delete.assert_called_once_with({"_id": ObjectId(TEST_MOVIE_ID)})

    @patch('src.routers.movies.get_collection')
    async def test_find_and_delete_not_found(self, mock_get_collection):
        """Should return error when movie does not exist."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_collection.find_one_and_delete.return_value = None
        mock_get_collection.return_value = mock_collection

        # Call the route handler
        from src.routers.movies import find_and_delete_movie
        with pytest.raises(HTTPException) as e:
            await find_and_delete_movie(TEST_MOVIE_ID)

        # Assertions
        assert e.value.status_code == 404
        assert "no movie" in str(e.value.detail.lower())

    async def test_find_and_delete_invalid_id(self):
        """Should return error when invalid ObjectId format is provided."""
        # Call the route handler
        from src.routers.movies import find_and_delete_movie
        with pytest.raises(HTTPException) as e:
            await find_and_delete_movie(INVALID_MOVIE_ID)

        # Assertions
        assert e.value.status_code == 400
        assert "invalid" in str(e.value.detail.lower())


@pytest.mark.unit
@pytest.mark.asyncio
class TestBatchUpdate:
    """Tests for PATCH /api/movies/ batch update endpoint."""

    @patch('src.routers.movies.get_collection')
    async def test_update_movies_batch_success(self, mock_get_collection):
        """Should update multiple movies matching filter."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_result = MagicMock()
        mock_result.matched_count = 5
        mock_result.modified_count = 5
        mock_collection.update_many.return_value = mock_result
        mock_get_collection.return_value = mock_collection

        # Create request
        from src.routers.movies import update_movies_batch
        request_body = {
            "filter": {"year": 2020},
            "update": {"$set": {"rated": "PG-13"}}
        }
        result = await update_movies_batch(request_body)

        # Assertions
        assert result.success is True
        assert result.data["matchedCount"] == 5
        assert result.data["modifiedCount"] == 5
        mock_collection.update_many.assert_called_once()

    @patch('src.routers.movies.get_collection')
    async def test_update_movies_batch_missing_filter(self, mock_get_collection):
        """Should return error when filter is missing."""
        mock_get_collection.return_value = AsyncMock()

        # Create request without filter
        from src.routers.movies import update_movies_batch
        request_body = {"update": {"$set": {"rated": "PG-13"}}}
        with pytest.raises(HTTPException) as e:
            await update_movies_batch(request_body)

        # Assertions
        assert e.value.status_code == 400
        assert "filter" in str(e.value.detail).lower()

    @patch('src.routers.movies.get_collection')
    async def test_update_movies_batch_missing_update(self, mock_get_collection):
        """Should return error when update is missing."""
        mock_get_collection.return_value = AsyncMock()

        # Create request without update
        from src.routers.movies import update_movies_batch
        request_body = {"filter": {"year": 2020}}
        with pytest.raises(HTTPException) as e:
            await update_movies_batch(request_body)

        # Assertions
        assert e.value.status_code == 400
        assert "update" in str(e.value.detail).lower()

    @patch('src.routers.movies.get_collection')
    async def test_update_movies_batch_no_matches(self, mock_get_collection):
        """Should return success with zero modified count when no movies match."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_result = MagicMock()
        mock_result.matched_count = 0
        mock_result.modified_count = 0
        mock_collection.update_many.return_value = mock_result
        mock_get_collection.return_value = mock_collection

        # Create request
        from src.routers.movies import update_movies_batch
        request_body = {
            "filter": {"year": 1800},
            "update": {"$set": {"rated": "PG-13"}}
        }
        result = await update_movies_batch(request_body)

        # Assertions
        assert result.success is True
        assert result.data["matchedCount"] == 0
        assert result.data["modifiedCount"] == 0



@pytest.mark.unit
@pytest.mark.asyncio
class TestSearchMovies:
    """Tests for GET /api/movies/search MongoDB Search endpoint."""

    @patch('src.routers.movies.execute_aggregation')
    async def test_search_movies_by_plot_success(self, mock_execute_aggregation):
        """Should successfully search movies by plot."""
        # Setup mock
        mock_execute_aggregation.return_value = [{
            "totalCount": [{"count": 2}],
            "results": [
                {"_id": ObjectId(TEST_MOVIE_ID), "title": "Test Movie 1", "plot": "A test plot", "year": 2024},
                {"_id": ObjectId("507f1f77bcf86cd799439012"), "title": "Test Movie 2", "plot": "Another test", "year": 2023}
            ]
        }]

        # Call the route handler
        from src.routers.movies import search_movies
        result = await search_movies(plot="test", search_operator="must")

        # Assertions
        assert result.success is True
        assert result.data.totalCount == 2
        assert len(result.data.movies) == 2
        assert result.data.movies[0].title == "Test Movie 1"
        mock_execute_aggregation.assert_called_once()

    @patch('src.routers.movies.execute_aggregation')
    async def test_search_movies_multiple_fields(self, mock_execute_aggregation):
        """Should search across multiple fields (directors and cast)."""
        # Setup mock
        mock_execute_aggregation.return_value = [{
            "totalCount": [{"count": 1}],
            "results": [
                {"_id": ObjectId(TEST_MOVIE_ID), "title": "Action Movie", "directors": ["John Doe"], "cast": ["Jane Smith"], "year": 2024}
            ]
        }]

        # Call the route handler
        from src.routers.movies import search_movies
        result = await search_movies(directors="John", cast="Jane", search_operator="must")

        # Assertions
        assert result.success is True
        assert result.data.totalCount == 1
        assert len(result.data.movies) == 1

    @patch('src.routers.movies.execute_aggregation')
    async def test_search_movies_with_pagination(self, mock_execute_aggregation):
        """Should support pagination parameters."""
        # Setup mock
        mock_execute_aggregation.return_value = [{
            "totalCount": [{"count": 100}],
            "results": [
                {"_id": ObjectId(TEST_MOVIE_ID), "title": f"Movie {i}", "year": 2024}
                for i in range(20)
            ]
        }]

        # Call the route handler
        from src.routers.movies import search_movies
        result = await search_movies(plot="test", limit=20, skip=20, search_operator="must")

        # Assertions
        assert result.success is True
        assert result.data.totalCount == 100
        assert len(result.data.movies) == 20

    async def test_search_movies_no_parameters(self):
        """Should return error when no search parameters provided."""
        from src.routers.movies import search_movies
        with pytest.raises(HTTPException) as e:
            await search_movies(search_operator="must")

        # Assertions
        assert e.value.status_code == 400
        assert "one search parameter" in str(e.value.detail).lower()

    async def test_search_movies_invalid_operator(self):
        """Should return error for invalid search operator."""
        from src.routers.movies import search_movies
        with pytest.raises(HTTPException) as e:
            await search_movies(plot="test", search_operator="invalid")

        # Assertions
        assert e.value.status_code == 400
        assert "invalid search operator" in str(e.value.detail).lower()

    @patch('src.routers.movies.execute_aggregation')
    async def test_search_movies_database_error(self, mock_execute_aggregation):
        """Should handle database errors gracefully."""
        # Setup mock to raise exception
        mock_execute_aggregation.side_effect = Exception("Database connection failed")

        # Call the route handler
        from src.routers.movies import search_movies
        with pytest.raises(HTTPException) as e:
            await search_movies(plot="test", search_operator="must")

        # Assertions
        assert e.value.status_code == 500
        assert "error" in str(e.value.detail).lower()

    @patch('src.routers.movies.execute_aggregation')
    async def test_search_movies_empty_results(self, mock_execute_aggregation):
        """Should return empty results when no movies match."""
        # Setup mock
        mock_execute_aggregation.return_value = [{
            "totalCount": [{"count": 0}],
            "results": []
        }]

        # Call the route handler
        from src.routers.movies import search_movies
        result = await search_movies(plot="nonexistent", search_operator="must")

        # Assertions
        assert result.success is True
        assert result.data.totalCount == 0
        assert len(result.data.movies) == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestVectorSearchMovies:
    """Tests for GET /api/movies/vector-search endpoint."""

    @patch('src.routers.movies.voyage_ai_available')
    async def test_vector_search_unavailable(self, mock_voyage_available):
        """Should return error when Voyage AI is not configured."""
        # Setup mock
        mock_voyage_available.return_value = False

        # Call the route handler
        from src.routers.movies import vector_search_movies
        from fastapi.responses import JSONResponse

        response = await vector_search_movies(q="action movie")

        # Assertions
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400

        # Parse the response body
        import json
        body = json.loads(response.body.decode())
        assert body["success"] is False
        assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "VOYAGE_API_KEY not configured" in body["message"]
        

    @patch('src.routers.movies.voyage_ai_available')
    @patch('src.routers.movies.voyageai.Client')
    @patch('src.routers.movies.get_embedding')
    @patch('src.routers.movies.get_collection')
    @patch('src.routers.movies.execute_aggregation_on_collection')
    async def test_vector_search_success(
        self,
        mock_execute_agg,
        mock_get_collection,
        mock_get_embedding,
        mock_voyage_client,
        mock_voyage_available
    ):
        """Should successfully perform vector search."""
        # Setup mocks
        mock_voyage_available.return_value = True
        mock_voyage_client.return_value = MagicMock()  # Mock the Voyage AI client
        mock_get_embedding.return_value = [0.1] * 2048  # Mock embedding vector
        mock_execute_agg.return_value = [
            {"_id": ObjectId(TEST_MOVIE_ID), "title": "Similar Movie 1", "plot": "Action packed", "score": 0.95},
            {"_id": ObjectId("507f1f77bcf86cd799439012"), "title": "Similar Movie 2", "plot": "More action", "score": 0.87}
        ]

        # Call the route handler
        from src.routers.movies import vector_search_movies
        result = await vector_search_movies(q="action movie", limit=10)

        # Assertions
        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0].title == "Similar Movie 1"
        assert result.data[0].score == 0.95
        mock_get_embedding.assert_called_once()
        mock_execute_agg.assert_called_once()

    @patch('src.routers.movies.voyage_ai_available')
    @patch('src.routers.movies.voyageai.Client')
    @patch('src.routers.movies.get_embedding')
    async def test_vector_search_embedding_error(self, mock_get_embedding, mock_voyage_client, mock_voyage_available):
        """Should handle embedding generation errors."""
        # Setup mocks
        mock_voyage_available.return_value = True
        mock_voyage_client.return_value = MagicMock()  # Mock the Voyage AI client
        mock_get_embedding.side_effect = Exception("Embedding API error")

        # Call the route handler
        from src.routers.movies import vector_search_movies
        with pytest.raises(HTTPException) as e:
            await vector_search_movies(q="action movie")

        # Assertions
        assert e.value.status_code == 500
        assert "error" in str(e.value.detail).lower()

    @patch('src.routers.movies.voyage_ai_available')
    @patch('src.routers.movies.voyageai.Client')
    @patch('src.routers.movies.get_embedding')
    @patch('src.routers.movies.get_collection')
    @patch('src.routers.movies.execute_aggregation_on_collection')
    async def test_vector_search_empty_results(
        self,
        mock_execute_agg,
        mock_get_collection,
        mock_get_embedding,
        mock_voyage_client,
        mock_voyage_available
    ):
        """Should return empty results when no similar movies found."""
        # Setup mocks
        mock_voyage_available.return_value = True
        mock_voyage_client.return_value = MagicMock()  # Mock the Voyage AI client
        mock_get_embedding.return_value = [0.1] * 2048
        mock_execute_agg.return_value = []

        # Call the route handler
        from src.routers.movies import vector_search_movies
        result = await vector_search_movies(q="very specific query", limit=10)

        # Assertions
        assert result.success is True
        assert len(result.data) == 0



@pytest.mark.unit
@pytest.mark.asyncio
class TestAggregationReportingByComments:
    """Tests for GET /api/movies/aggregations/reportingByComments endpoint."""

    @patch('src.routers.movies.execute_aggregation')
    async def test_aggregate_movies_recent_commented_success(self, mock_execute_aggregation):
        """Should successfully aggregate movies with recent comments."""
        # Setup mock
        mock_execute_aggregation.return_value = [
            {
                "_id": ObjectId(TEST_MOVIE_ID),
                "title": "Popular Movie",
                "year": 2024,
                "genres": ["Action"],
                "imdbRating": 8.5,
                "recentComments": [
                    {"userName": "John", "userEmail": "john@test.com", "text": "Great movie!", "date": "2024-01-01"},
                    {"userName": "Jane", "userEmail": "jane@test.com", "text": "Loved it!", "date": "2024-01-02"}
                ],
                "totalComments": 10
            }
        ]

        # Call the route handler
        from src.routers.movies import aggregate_movies_recent_commented
        result = await aggregate_movies_recent_commented(limit=10, movie_id=None)

        # Assertions
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["title"] == "Popular Movie"
        assert result.data[0]["totalComments"] == 10
        assert len(result.data[0]["recentComments"]) == 2
        mock_execute_aggregation.assert_called_once()

    @patch('src.routers.movies.execute_aggregation')
    async def test_aggregate_movies_by_movie_id(self, mock_execute_aggregation):
        """Should filter by specific movie ID."""
        # Setup mock
        mock_execute_aggregation.return_value = [
            {
                "_id": ObjectId(TEST_MOVIE_ID),
                "title": "Specific Movie",
                "year": 2024,
                "totalComments": 5,
                "recentComments": []
            }
        ]

        # Call the route handler
        from src.routers.movies import aggregate_movies_recent_commented
        result = await aggregate_movies_recent_commented(movie_id=TEST_MOVIE_ID)

        # Assertions
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["_id"] == TEST_MOVIE_ID

    async def test_aggregate_movies_invalid_movie_id(self):
        """Should return error for invalid movie ID format."""
        from src.routers.movies import aggregate_movies_recent_commented
        with pytest.raises(HTTPException) as e:
            await aggregate_movies_recent_commented(movie_id="invalid_id")

        # Assertions
        assert e.value.status_code == 400
        assert "movie_id is not" in str(e.value.detail).lower()

    @patch('src.routers.movies.execute_aggregation')
    async def test_aggregate_movies_database_error(self, mock_execute_aggregation):
        """Should handle database errors gracefully."""
        # Setup mock to raise exception
        mock_execute_aggregation.side_effect = Exception("Aggregation failed")

        # Call the route handler
        from src.routers.movies import aggregate_movies_recent_commented
        with pytest.raises(HTTPException) as e:
            await aggregate_movies_recent_commented(limit=10, movie_id=None)

        # Assertions
        assert e.value.status_code == 500
        assert "error" in str(e.value.detail).lower()

    @patch('src.routers.movies.execute_aggregation')
    async def test_aggregate_movies_empty_results(self, mock_execute_aggregation):
        """Should return empty results when no movies have comments."""
        # Setup mock
        mock_execute_aggregation.return_value = []

        # Call the route handler
        from src.routers.movies import aggregate_movies_recent_commented
        result = await aggregate_movies_recent_commented(limit=10, movie_id=None)

        # Assertions
        assert result.success is True
        assert len(result.data) == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestAggregationReportingByYear:
    """Tests for GET /api/movies/aggregations/reportingByYear endpoint."""

    @patch('src.routers.movies.execute_aggregation')
    async def test_aggregate_movies_by_year_success(self, mock_execute_aggregation):
        """Should successfully aggregate movies by year with statistics."""
        # Setup mock
        mock_execute_aggregation.return_value = [
            {"year": 2024, "movieCount": 150, "averageRating": 7.5, "highestRating": 9.5, "lowestRating": 5.0, "totalVotes": 50000},
            {"year": 2023, "movieCount": 200, "averageRating": 7.2, "highestRating": 9.0, "lowestRating": 4.5, "totalVotes": 75000}
        ]

        # Call the route handler
        from src.routers.movies import aggregate_movies_by_year
        result = await aggregate_movies_by_year()

        # Assertions
        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]["year"] == 2024
        assert result.data[0]["movieCount"] == 150
        assert result.data[0]["averageRating"] == 7.5
        mock_execute_aggregation.assert_called_once()

    @patch('src.routers.movies.execute_aggregation')
    async def test_aggregate_movies_by_year_database_error(self, mock_execute_aggregation):
        """Should handle database errors gracefully."""
        # Setup mock to raise exception
        mock_execute_aggregation.side_effect = Exception("Aggregation pipeline failed")

        # Call the route handler
        from src.routers.movies import aggregate_movies_by_year
        with pytest.raises(HTTPException) as e:
            await aggregate_movies_by_year()

        # Assertions
        assert e.value.status_code == 500
        assert "error" in str(e.value.detail).lower()

    @patch('src.routers.movies.execute_aggregation')
    async def test_aggregate_movies_by_year_empty_results(self, mock_execute_aggregation):
        """Should return empty results when no valid year data."""
        # Setup mock
        mock_execute_aggregation.return_value = []

        # Call the route handler
        from src.routers.movies import aggregate_movies_by_year
        result = await aggregate_movies_by_year()

        # Assertions
        assert result.success is True
        assert len(result.data) == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestAggregationReportingByDirectors:
    """Tests for GET /api/movies/aggregations/reportingByDirectors endpoint."""

    @patch('src.routers.movies.execute_aggregation')
    async def test_aggregate_directors_most_movies_success(self, mock_execute_aggregation):
        """Should successfully aggregate directors with most movies."""
        # Setup mock
        mock_execute_aggregation.return_value = [
            {"director": "Steven Spielberg", "movieCount": 50, "averageRating": 8.2},
            {"director": "Martin Scorsese", "movieCount": 45, "averageRating": 8.5},
            {"director": "Christopher Nolan", "movieCount": 40, "averageRating": 8.7}
        ]

        # Call the route handler
        from src.routers.movies import aggregate_directors_most_movies
        result = await aggregate_directors_most_movies(limit=20)

        # Assertions
        assert result.success is True
        assert len(result.data) == 3
        assert result.data[0]["director"] == "Steven Spielberg"
        assert result.data[0]["movieCount"] == 50
        assert result.data[0]["averageRating"] == 8.2
        mock_execute_aggregation.assert_called_once()

    @patch('src.routers.movies.execute_aggregation')
    async def test_aggregate_directors_with_custom_limit(self, mock_execute_aggregation):
        """Should respect custom limit parameter."""
        # Setup mock
        mock_execute_aggregation.return_value = [
            {"director": "Director 1", "movieCount": 10, "averageRating": 7.0}
        ]

        # Call the route handler
        from src.routers.movies import aggregate_directors_most_movies
        result = await aggregate_directors_most_movies(limit=5)

        # Assertions
        assert result.success is True
        # Verify the aggregation was called (limit is applied in pipeline)
        mock_execute_aggregation.assert_called_once()

    @patch('src.routers.movies.execute_aggregation')
    async def test_aggregate_directors_database_error(self, mock_execute_aggregation):
        """Should handle database errors gracefully."""
        # Setup mock to raise exception
        mock_execute_aggregation.side_effect = Exception("Pipeline execution failed")

        # Call the route handler
        from src.routers.movies import aggregate_directors_most_movies
        with pytest.raises(HTTPException) as e: 
            await aggregate_directors_most_movies()

        # Assertions
        assert e.value.status_code == 500
        assert "error" in str(e.value.detail).lower()

    @patch('src.routers.movies.execute_aggregation')
    async def test_aggregate_directors_empty_results(self, mock_execute_aggregation):
        """Should return empty results when no directors found."""
        # Setup mock
        mock_execute_aggregation.return_value = []

        # Call the route handler
        from src.routers.movies import aggregate_directors_most_movies
        result = await aggregate_directors_most_movies()

        # Assertions
        assert result.success is True
        assert len(result.data) == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetDistinctGenres:
    """Tests for GET /api/movies/genres endpoint."""

    @patch('src.routers.movies.get_collection')
    async def test_get_distinct_genres_success(self, mock_get_collection):
        """Should return list of distinct genres sorted alphabetically."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_collection.distinct.return_value = ["Drama", "Action", "Comedy", "Horror", "Sci-Fi"]
        mock_get_collection.return_value = mock_collection

        # Call the route handler
        from src.routers.movies import get_distinct_genres
        result = await get_distinct_genres()

        # Assertions
        assert result.success is True
        assert len(result.data) == 5
        # Verify alphabetical sorting
        assert result.data == ["Action", "Comedy", "Drama", "Horror", "Sci-Fi"]
        mock_collection.distinct.assert_called_once_with("genres")

    @patch('src.routers.movies.get_collection')
    async def test_get_distinct_genres_empty_list(self, mock_get_collection):
        """Should return empty list when no genres exist."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_collection.distinct.return_value = []
        mock_get_collection.return_value = mock_collection

        # Call the route handler
        from src.routers.movies import get_distinct_genres
        result = await get_distinct_genres()

        # Assertions
        assert result.success is True
        assert len(result.data) == 0

    @patch('src.routers.movies.get_collection')
    async def test_get_distinct_genres_filters_null_and_empty(self, mock_get_collection):
        """Should filter out null and empty genre values."""
        # Setup mock
        mock_collection = AsyncMock()
        mock_collection.distinct.return_value = ["Action", None, "", "Drama", "Comedy"]
        mock_get_collection.return_value = mock_collection

        # Call the route handler
        from src.routers.movies import get_distinct_genres
        result = await get_distinct_genres()

        # Assertions
        assert result.success is True
        assert len(result.data) == 3
        assert "Action" in result.data
        assert "Drama" in result.data
        assert "Comedy" in result.data
        assert None not in result.data
        assert "" not in result.data

    @patch('src.routers.movies.get_collection')
    async def test_get_distinct_genres_database_error(self, mock_get_collection):
        """Should handle database errors gracefully."""
        # Setup mock to raise exception
        mock_collection = AsyncMock()
        mock_collection.distinct.side_effect = Exception("Database connection failed")
        mock_get_collection.return_value = mock_collection

        # Call the route handler
        from src.routers.movies import get_distinct_genres
        with pytest.raises(HTTPException) as exc_info:
            await get_distinct_genres()

        # Assertions
        assert exc_info.value.status_code == 500
        assert "Database error" in str(exc_info.value.detail)
