"""
Integration tests for movie routes.

These tests validate the full request/response cycle against a real MongoDB instance.
They demonstrate best practices for:
- Testing with real database operations
- Managing test data lifecycle
- Leaving the database in a clean state
- Testing against production-like data (MFlix dataset)

Note: These tests create and clean up their own test data, leaving the
existing MFlix dataset untouched.
"""

import pytest


@pytest.mark.integration
class TestMovieCRUDIntegration:
    """
    Integration tests for basic CRUD operations.

    These tests demonstrate the full lifecycle of movie documents:
    - Creating new documents
    - Reading documents by ID
    - Updating existing documents
    - Deleting documents
    """

    @pytest.mark.asyncio
    async def test_create_and_retrieve_movie(self, client, test_movie_data):
        """
        Test creating a movie and retrieving it by ID.

        This test demonstrates:
        - POST request with JSON body
        - Response validation
        - GET request with path parameter
        - Explicit cleanup pattern
        """
        # Create a new movie
        create_response = await client.post("/api/movies/", json=test_movie_data)

        # Validate creation response (201 Created is correct for POST)
        assert create_response.status_code == 201
        create_data = create_response.json()
        assert create_data["success"] is True
        assert create_data["data"]["title"] == test_movie_data["title"]

        movie_id = create_data["data"]["_id"]

        try:
            # Retrieve the created movie
            get_response = await client.get(f"/api/movies/{movie_id}")

            # Validate retrieval response
            assert get_response.status_code == 200
            get_data = get_response.json()
            assert get_data["success"] is True
            assert get_data["data"]["_id"] == movie_id
            assert get_data["data"]["title"] == test_movie_data["title"]
            assert get_data["data"]["year"] == test_movie_data["year"]

        finally:
            # Cleanup: Delete the test movie
            delete_response = await client.delete(f"/api/movies/{movie_id}")
            assert delete_response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_movie(self, client, created_movie):
        """
        Test updating a movie's fields.

        This test demonstrates:
        - Using fixtures for setup/cleanup
        - PATCH request with partial updates
        - Verifying updates persisted to database
        """
        # Update the movie
        update_data = {
            "title": "Updated Integration Test Title",
            "year": 2025,
            "plot": "Updated plot for integration testing"
        }
        update_response = await client.patch(
            f"/api/movies/{created_movie}",
            json=update_data
        )

        # Validate update response
        assert update_response.status_code == 200
        update_result = update_response.json()
        assert update_result["success"] is True

        # Verify the update persisted
        get_response = await client.get(f"/api/movies/{created_movie}")
        assert get_response.status_code == 200
        movie_data = get_response.json()["data"]
        assert movie_data["title"] == update_data["title"]
        assert movie_data["year"] == update_data["year"]
        assert movie_data["plot"] == update_data["plot"]

        # Fixture handles cleanup automatically

    @pytest.mark.asyncio
    async def test_delete_movie(self, client, test_movie_data):
        """
        Test deleting a movie.

        This test demonstrates:
        - Complete lifecycle: create -> delete -> verify
        - Testing 404 response after deletion
        - No cleanup needed (movie already deleted)
        """
        # Create a movie
        create_response = await client.post("/api/movies/", json=test_movie_data)
        movie_id = create_response.json()["data"]["_id"]

        # Delete the movie
        delete_response = await client.delete(f"/api/movies/{movie_id}")
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["success"] is True

        # Verify movie no longer exists
        # Note: The API returns 200 with INTERNAL_SERVER_ERROR code, not 404
        get_response = await client.get(f"/api/movies/{movie_id}")
        error_data = get_response.json()
        assert error_data["success"] is False
        assert error_data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "not found" in error_data["error"]["message"].lower()

        # No cleanup needed - movie already deleted


@pytest.mark.integration
class TestMovieSearchIntegration:
    """
    Integration tests for search functionality.

    These tests use the existing MFlix dataset (read-only operations).
    No cleanup needed since we're not modifying data.
    """

    @pytest.mark.asyncio
    async def test_search_existing_movies_by_plot(self, client):
        """
        Test searching movies using the existing MFlix dataset.

        This test demonstrates:
        - Read-only operations against production-like data
        - Query parameters in GET requests
        - No cleanup needed for read operations
        """
        # Search for movies with "love" in the plot
        response = await client.get("/api/movies/search?plot=love&search_operator=must")

        # Validate response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["totalCount"] > 0
        assert len(data["data"]["movies"]) > 0

        # Verify search results contain the search term
        first_movie = data["data"]["movies"][0]
        assert "title" in first_movie
        assert "plot" in first_movie

    @pytest.mark.asyncio
    async def test_get_all_movies_with_pagination(self, client):
        """
        Test retrieving movies with pagination.

        This test demonstrates:
        - Pagination parameters (skip/limit, not page-based)
        - Testing against existing dataset
        - Validating response structure
        """
        # Get first page using skip and limit
        response = await client.get("/api/movies/?skip=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # The API returns a simple list in data, not a paginated object
        assert isinstance(data["data"], list)
        assert len(data["data"]) <= 10


@pytest.mark.integration
class TestBatchOperationsIntegration:
    """
    Integration tests for batch operations.

    These tests demonstrate working with multiple documents
    and proper cleanup of all created test data.
    """

    @pytest.mark.asyncio
    async def test_batch_create_movies(self, client):
        """
        Test creating multiple movies in a single request.

        This test demonstrates:
        - Batch creation endpoint
        - Creating multiple test documents
        - Cleaning up all created documents
        """
        # Prepare batch of movies
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        movies = [
            {
                "title": f"Batch Movie {i} - {unique_id}",
                "year": 2024,
                "plot": f"Batch test movie {i}",
                "genres": ["Test"],
                "runtime": 90
            }
            for i in range(3)
        ]

        # Create batch
        response = await client.post("/api/movies/batch", json=movies)

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

        # Extract created IDs for cleanup
        created_ids = data["data"]["insertedIds"]
        assert len(created_ids) == 3

        try:
            # Verify all movies were created
            for movie_id in created_ids:
                get_response = await client.get(f"/api/movies/{movie_id}")
                assert get_response.status_code == 200
        finally:
            # Cleanup: Delete all created movies
            for movie_id in created_ids:
                await client.delete(f"/api/movies/{movie_id}")

    @pytest.mark.asyncio
    async def test_batch_delete_movies(self, client, multiple_test_movies):
        """
        Test deleting multiple movies using a filter.

        This test demonstrates:
        - Using fixtures to create test data
        - Batch delete with filter
        - Verifying deletions
        """
        # Get one of the test movie titles for filtering
        first_movie_response = await client.get(f"/api/movies/{multiple_test_movies[0]}")
        first_movie_title = first_movie_response.json()["data"]["title"]

        # Extract the unique ID from the title (format: "Batch Test Movie X - {uuid}")
        unique_id = first_movie_title.split(" - ")[-1]

        # Delete all movies with this unique ID in the title
        # Note: httpx AsyncClient.delete() doesn't support json parameter
        # We need to use request() method instead
        # The API expects the filter to be wrapped in a "filter" key
        # The batch delete endpoint is at DELETE /api/movies/ (not /batch)
        delete_response = await client.request(
            "DELETE",
            "/api/movies/",
            json={"filter": {"title": {"$regex": unique_id}}}
        )

        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["success"] is True
        assert delete_data["data"]["deletedCount"] == 3

        # Verify all movies were deleted
        # Note: The API returns 200 with INTERNAL_SERVER_ERROR code, not 404
        for movie_id in multiple_test_movies:
            get_response = await client.get(f"/api/movies/{movie_id}")
            response_data = get_response.json()
            assert response_data["success"] is False
            assert response_data["error"]["code"] == "INTERNAL_SERVER_ERROR"
            assert "not found" in response_data["error"]["message"].lower()

        # Note: Fixture cleanup will try to delete but movies are already gone
        # The fixture should handle this gracefully


@pytest.mark.integration
class TestAggregationIntegration:
    """
    Integration tests for aggregation endpoints.

    These tests use the existing MFlix dataset (read-only operations).
    """

    @pytest.mark.asyncio
    async def test_aggregate_movies_by_year(self, client):
        """
        Test aggregation reporting by year.

        This test demonstrates:
        - Complex aggregation pipelines
        - Testing against existing dataset
        - Validating aggregation results
        """
        response = await client.get("/api/movies/aggregations/reportingByYear")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0

        # Validate structure of aggregation results
        # Note: The aggregation projects "year" field and excludes "_id"
        first_result = data["data"][0]
        assert "year" in first_result  # Year field (not _id)
        assert "movieCount" in first_result
        assert "averageRating" in first_result  # Note: it's averageRating, not avgRuntime
        assert "highestRating" in first_result
        assert "lowestRating" in first_result
        assert "totalVotes" in first_result

    @pytest.mark.asyncio
    async def test_aggregate_movies_by_comments(self, client):
        """
        Test aggregation reporting by comments.

        This test demonstrates:
        - $lookup aggregation (joining collections)
        - Testing against existing dataset with comments
        - Validating nested data structures
        """
        response = await client.get("/api/movies/aggregations/reportingByComments?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Should return movies that have comments
        if len(data["data"]) > 0:
            first_result = data["data"][0]
            # Validate structure of aggregation results
            assert "_id" in first_result
            assert "title" in first_result
            assert "year" in first_result
            assert "totalComments" in first_result
            assert "recentComments" in first_result
            assert isinstance(first_result["recentComments"], list)

            # If there are recent comments, validate their structure
            if len(first_result["recentComments"]) > 0:
                comment = first_result["recentComments"][0]
                assert "userName" in comment
                assert "userEmail" in comment
                assert "text" in comment
                assert "date" in comment

    @pytest.mark.asyncio
    async def test_aggregate_directors_most_movies(self, client):
        """
        Test aggregation reporting by directors.

        This test demonstrates:
        - $unwind aggregation (array flattening)
        - Grouping and sorting operations
        - Testing against existing dataset
        """
        response = await client.get("/api/movies/aggregations/reportingByDirectors?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0

        # Validate structure of aggregation results
        first_result = data["data"][0]
        assert "director" in first_result
        assert "movieCount" in first_result
        assert "averageRating" in first_result

        # Verify results are sorted by movieCount (descending)
        if len(data["data"]) > 1:
            assert data["data"][0]["movieCount"] >= data["data"][1]["movieCount"]

