from fastapi import APIRouter, Query, Path, Body, HTTPException
from fastapi.responses import JSONResponse
from src.database.mongo_client import get_collection, voyage_ai_available
from src.models.models import VectorSearchResult, CreateMovieRequest, Movie, SuccessResponse, UpdateMovieRequest, SearchMoviesResponse
from typing import Any, List, Optional
from src.utils.successResponse import create_success_response
from src.utils.errorResponse import create_error_response
from src.utils.exceptions import VoyageAuthError, VoyageAPIError
from bson import ObjectId, errors
import re
from bson.errors import InvalidId
import voyageai
import voyageai.error as voyage_error
import os


'''
This file contains all the business logic for movie operations.
Each method demonstrates different MongoDB operations using the PyMongo driver.

The /search and /vector-search endpoints are at the top of the file because they must be
before the /{id} endpoint to avoid route conflicts where the /search and /vector-search
endpoints match the /{id} pattern rather than the intended paths.

Implemented Endpoints:

- GET /api/movies/search :
    Search movies using MongoDB Search across the plot, fullplot, directors, writers, and cast fields.
    Supports compound search operators and fuzzy matching.

- GET /api/movies/vector-search :
    Search movies using MongoDB Vector Search to enable semantic search capabilities over
    the plot field.

- GET /api/movies/genres :
    Retrieve all distinct genre values from the movies collection.
    Demonstrates the distinct() operation.

- GET /api/movies/{id} :
    Retrieve a single movie by its ID.

- GET /api/movies/ :
    Retrieve a list of movies with optional filtering, sorting, and pagination.
    Supports text search, genre, year, rating filters, and customizable sorting.

- POST /api/movies/ :
    Create a new movie.

- POST /api/movies/batch :
    Create multiple movies in a single request.

- PATCH /api/movies/{movie_id} :
    Update a single movie by its ID.

- PATCH /api/movies/ :
    Batch update movies matching the given filter.

- DELETE /api/movies/{id} :
    Delete a single movie by its ID.

- DELETE /api/movies/ :
    Delete multiple movies matching the given filter.

- DELETE /api/movies/{id}/find-and-delete :
    Find and delete a movie in a single atomic operation.

- GET /api/movies/aggregations/reportingByComments :
    Aggregate movies with their most recent comments using MongoDB $lookup aggregation.

- GET /api/movies/aggregations/reportingByYear :
    Aggregate movies by year with average rating and movie count.

- GET /api/movies/aggregations/reportingByDirectors :
    Aggregate directors with the most movies and their statistics.

Helper Functions:
- execute_aggregation(pipeline): Executes a MongoDB aggregation pipeline and returns the
results.
- execute_aggregation_on_collection(collection, pipeline): Executes a MongoDB aggregation pipeline on a specific collection and returns the results.
- get_embedding(data, input_type): Creates the vector embedding for a given input using the specified input type.
'''

router = APIRouter()

#----------------------------------------------------------------------------------------------------------
# MongoDB Search
#
# MongoDB Search based on searching the plot, fullplot, directors, writers, and cast fields.
# This fuzzy operator is being used to allow for some misspellings in the search terms
# but that allows for very generous matching. This can be adjusted as needed.
#----------------------------------------------------------------------------------------------------------
"""

    GET /api/movies/search

    Search movies using MongoDB Search across the plot, fullplot, directors, writers, and cast fields.
    You can combine multiple fields in a single query, and control how they are combined using the `search_operator` parameter.

    Query Parameters:
        plot (str, optional): Text to search against the plot field.
        fullplot (str, optional): Text to search against the fullplot field.
        directors (str, optional): Text to search against the directors field.
        writers (str, optional): Text to search against the writers field.
        cast (str, optional): Text to search against the cast field.
        limit (int, optional): Number of results to return (default: 20)
        skip (int, optional): Number of results to skip for pagination (default: 0)
        search_operator (str, optional): How to combine multiple search fields.
            Must be one of "must", "should", "mustNot", or "filter". Default is "must".

    Returns:
        SuccessResponse[SearchMoviesResponse]: A response object containing the list of matching movies and total count.
"""
@router.get(
    "/search",
    response_model=SuccessResponse[SearchMoviesResponse],
    status_code = 200,
    summary="Search movies using MongoDB Search."
)
async def search_movies(
    plot: Optional[str] = None,
    fullplot: Optional[str] = None,
    directors: Optional[str] = None,
    writers: Optional[str] = None,
    cast: Optional[str] = None,
    limit:int = Query(default=20, ge=1, le=100),
    skip:int = Query(default=0, ge=0),
    search_operator: str = Query(default="must", alias="searchOperator")
) -> SuccessResponse[SearchMoviesResponse]:

    search_phrases = []

    # Validate the search_operator parameter to ensure it's a valid compound operator
    valid_operators = {"must", "should", "mustNot", "filter"}

    if search_operator not in valid_operators:
        raise HTTPException(
            status_code = 400,
            detail=f"Invalid search operator '{search_operator}'. The search operator must be one of {valid_operators}."
        )

    # Build the search_phrases list based on which fields were provided by the user.
    # Each phrase becomes a separate clause in the MongoDB Search compound query.

    if plot is not None:
        search_phrases.append({
            # The phrase operator performs an exact phrase match on the specified field. This is useful for searching for specific phrases within text fields.
            # The text operator is more flexible and allows for fuzzy matching, making it suitable for fields like names where typos may occur.
            "phrase": {
                "query": plot,
                "path": "plot",
            }
        })
    if fullplot is not None:
        search_phrases.append({
            "phrase": {
                "query": fullplot,
                "path": "fullplot",
            }
        })
    if directors is not None:
        # Use compound operator with "should" clauses to create a scoring hierarchy:
        # 1. phrase match (highest score) - exact phrase in same array element
        # 2. text match without fuzzy (high score) - all terms present, exact spelling
        # 3. text match with fuzzy (lower score) - typo-tolerant fallback; update fuzzy settings as needed
        # For more details, see: https://www.mongodb.com/docs/atlas/atlas-search/operators-collectors/text/
        search_phrases.append({
            "compound": {
                "should": [
                    # Highest score: exact phrase match
                    {"phrase": {"query": directors, "path": "directors"}},
                    # High score: exact text match (all terms, no fuzzy)
                    {"text": {"query": directors, "path": "directors", "matchCriteria": "all"}},
                    # Lower score: fuzzy match (typo tolerance)
                    {"text": {"query": directors, "path": "directors", "matchCriteria": "all",
                              "fuzzy": {"maxEdits": 1, "prefixLength": 2}}} # Allow up to 1 edit, require first 2 characters to match
                ],
                "minimumShouldMatch": 1
            }
        })

    if writers is not None:
        # See comments above regarding compound scoring hierarchy.
        search_phrases.append({
            "compound": {
                "should": [
                    {"phrase": {"query": writers, "path": "writers"}},
                    {"text": {"query": writers, "path": "writers", "matchCriteria": "all"}},
                    {"text": {"query": writers, "path": "writers", "matchCriteria": "all",
                              "fuzzy": {"maxEdits": 1, "prefixLength": 2}}}
                ],
                "minimumShouldMatch": 1
            }
        })

    if cast is not None:
        # See comments above regarding compound scoring hierarchy.
        search_phrases.append({
            "compound": {
                "should": [
                    {"phrase": {"query": cast, "path": "cast"}},
                    {"text": {"query": cast, "path": "cast", "matchCriteria": "all"}},
                    {"text": {"query": cast, "path": "cast", "matchCriteria": "all",
                              "fuzzy": {"maxEdits": 1, "prefixLength": 2}}}
                ],
                "minimumShouldMatch": 1
            }
        })

    if not search_phrases:
        raise HTTPException(
            status_code = 400,
            detail="At least one search parameter must be provided."
        )

    # Build the aggregation pipeline for MongoDB Search.
    # The $search stage uses the specified compound operator (must, should, etc.)
    aggregation_pipeline = [
        {
            "$search": {
                "index": "movieSearchIndex",
                "compound": {
                    search_operator: search_phrases
                }
            }
        },
        {
            "$facet": {
                "totalCount": [
                    {"$count": "count"}
                ],
                "results": [
                    {"$skip": skip},
                    {"$limit": limit},
                    # Project only the fields needed in the response
                    {
                        "$project": {
                            "_id": 1,
                            "title": 1,
                            "year": 1,
                            "plot": 1,
                            "fullplot": 1,
                            "released":1,
                            "runtime": 1,
                            "poster": 1,
                            "genres": 1,
                            "directors": 1,
                            "writers": 1,
                            "cast": 1,
                            "countries": 1,
                            "languages": 1,
                            "rated": 1,
                            "awards": 1,
                            "imdb": 1,
                        }
                    }
                ]
            }
        }
    ]

    # Execute the aggregation pipeline using the helper function
    try:
        results = await execute_aggregation(aggregation_pipeline)
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"An error occurred while performing the search: {str(e)}"
        )
        

    # Extract total count and movies from facet results with proper bounds checking
    if not results or len(results) == 0:
        return create_success_response(
            SearchMoviesResponse(movies=[], totalCount=0),
            "No movies found matching the search criteria."
        )

    facet_result = results[0]

    # Safely extract total count
    total_count_array = facet_result.get("totalCount", [])
    total_count = total_count_array[0].get("count", 0) if total_count_array else 0

    # Safely extract movies data
    movies_data = facet_result.get("results", [])

    # Convert ObjectId to string for each movie in the results
    movies = []
    for movie in movies_data:
        movie["_id"] = str(movie["_id"])
        movies.append(movie)

    return create_success_response(
        SearchMoviesResponse(movies=movies, totalCount=total_count),
        f"Found {total_count} movies matching the search criteria."
      )

#----------------------------------------------------------------------------------------------------------
# MongoDB Vector Search
#
# MongoDB Vector Search based on searching the plot_embedding_voyage_3_large field.
#----------------------------------------------------------------------------------------------------------
"""

    GET /api/movies/vector-search

    Search movies using MongoDB Vector Search to find movies with similar plots.
    Uses embeddings generated by the Voyage AI model to perform semantic similarity search.

    Query Parameters:
        q (str, required): Search query text to find movies with similar plots.
        limit (int, optional): Number of results to return (default: 10, max: 50).

    Returns:
        SuccessResponse[List[VectorSearchResult]]: A response object containing movies with similarity scores.
        Each result includes:
            - _id: Movie ObjectId
            - title: Movie title
            - plot: Movie plot text
            - score: Vector search similarity score (0.0 to 1.0, higher = more similar)
"""
# Specify your Voyage AI embedding model
model = "voyage-3-large"
outputDimension = 2048 #Set to 2048 to match the dimensions of the collection's embeddings

# Vector Search Endpoint
@router.get("/vector-search", response_model=SuccessResponse[List[VectorSearchResult]])
async def vector_search_movies(
    q: str = Query(..., description="Search query to find similar movies by plot"),
    limit: int = Query(default=10, ge=1, le=50, description="Number of results to return")
):
    """
    Vector search endpoint for finding movies with similar plots.

    Args:
        q: The search query string
        limit: Maximum number of results to return

    Returns:
        SuccessResponse containing a list of movies with similarity scores
    """
    # Check if Voyage AI API key is configured
    if not voyage_ai_available():
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                message="Vector search unavailable: VOYAGE_API_KEY not configured. Please add your API key to the .env file",
                code="SERVICE_UNAVAILABLE"
            )
        )

    try:
        # The vector search index was already created at startup time
        # Generate embedding for the search query (client is created inside get_embedding)
        query_embedding = get_embedding(q, input_type="query")

        # Get the embedded movies collection
        embedded_movies_collection = get_collection("embedded_movies")

        # Define vector search pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "plot_embedding_voyage_3_large",
                    "queryVector": query_embedding, #2048
                    "numCandidates": limit * 20,  # We recommend searching 20 times higher than the limit to improve result relevance
                    "limit": limit
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "title": 1,
                    "plot": 1,
                    "poster": 1,
                    "year": {
                        "$cond": {
                            "if": {
                                "$and": [
                                    {"$ne": ["$year", None]},
                                    {"$eq": [{"$type": "$year"}, "int"]}
                                ]
                            },
                            "then": "$year",
                            "else": None
                        }
                    },
                    "genres": 1,
                    "directors": 1,
                    "cast": 1,
                    "score": {
                        "$meta": "vectorSearchScore"
                    }
                }
            }
        ]

        raw_results = await execute_aggregation_on_collection(embedded_movies_collection, pipeline)

        # Convert ObjectId to string and create VectorSearchResult objects
        for result in raw_results:
            if "_id" in result and result["_id"]:
                try:
                    result["_id"] = str(result["_id"])
                except (InvalidId, TypeError):
                    # Handle invalid ObjectId conversion
                    result["_id"] = str(result["_id"]) if result["_id"] else None

        # This code converts the raw results into VectorSearchResult objects
        results = [VectorSearchResult(**doc) for doc in raw_results]

        return create_success_response(
            results,
            f"Found {len(results)} similar movies for query: '{q}'"
        )

    except VoyageAuthError:
        # Re-raise custom exceptions to be handled by the exception handlers
        raise
    except VoyageAPIError:
        # Re-raise custom exceptions to be handled by the exception handlers
        raise
    except Exception as e:
        # Log the error for debugging
        print(f"Vector search error: {str(e)}")

        # Handle generic errors
        raise HTTPException(
            status_code=500,
            detail=f"Error performing vector search: {str(e)}"
        )

"""
    GET /api/movies/genres

    Retrieve all distinct genre values from the movies collection.
    Demonstrates the distinct() operation.

    Returns:
        SuccessResponse[List[str]]: A response object containing the list of unique genres, sorted alphabetically.
"""

@router.get("/genres",
            response_model=SuccessResponse[List[str]],
            status_code=200,
            summary="Retrieve all distinct genres from the movies collection.")
async def get_distinct_genres():
    movies_collection = get_collection("movies")

    try:
        # Use distinct() to get all unique values from the genres array field
        # MongoDB automatically flattens array fields when using distinct()
        genres = await movies_collection.distinct("genres")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error occurred: {str(e)}"
        )

    # Filter out null/empty values and sort alphabetically
    valid_genres = sorted([
        genre for genre in genres
        if isinstance(genre, str) and len(genre) > 0
    ])

    return create_success_response(valid_genres, f"Found {len(valid_genres)} distinct genres")

"""
    GET /api/movies/{id}
    Retrieve a single movie by its ID.
    Path Parameters:
        id (str): The ObjectId of the movie to retrieve.
    Returns:
        SuccessResponse[Movie]: A response object containing the movie data.
"""

@router.get("/{id}",
            response_model=SuccessResponse[Movie],
            status_code = 200,
            summary="Retrieve a single movie by its ID.")
async def get_movie_by_id(id: str):
    # Validate ObjectId format
    try:
        object_id = ObjectId(id)
    except errors.InvalidId:
        raise HTTPException(
            status_code = 400,
            detail=f"The provided ID '{id}' is not a valid ObjectId"
        )

    movies_collection = get_collection("movies")
    try:
        movie = await movies_collection.find_one({"_id": object_id})
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"Database error occurred: {str(e)}"
        )
        

    if movie is None:
        raise HTTPException(
            status_code = 404,
            detail=f"No movie found with ID: {id}"
        )

    movie["_id"] = str(movie["_id"]) # Convert ObjectId to string

    return create_success_response(movie, "Movie retrieved successfully")

"""
    GET /api/movies/

    Retrieve a list of movies with optional filtering, sorting, and pagination.

    Query Parameters:
        q (str, optional): Text search query (searches title, plot, fullplot).
        genre (str, optional): Filter by genre.
        year (int, optional): Filter by year.
        min_rating (float, optional): Minimum IMDB rating.
        max_rating (float, optional): Maximum IMDB rating.
        limitNum (int, optional): Number of results to return (default: 20, max: 100).
        skipNum (int, optional): Number of documents to skip for pagination (default: 0).
        sortBy (str, optional): Field to sort by (default: "title").
        sort_order (str, optional): Sort direction, "asc" or "desc" (default: "asc").

    Returns:
        SuccessResponse[List[Movie]]: A response object containing the list of movies and metadata.
"""

@router.get("/",
            response_model=SuccessResponse[List[Movie]],
            status_code = 200,
            summary="Retrieve a list of movies with optional filtering, sorting, and pagination.")
# Validate the query parameters using FastAPI's Query functionality.
async def get_all_movies(
    q:str = Query(default=None),
    title: str = Query(default=None),
    genre:str = Query(default=None),
    year:int = Query(default=None),
    min_rating:float = Query(default=None, alias="minRating"),
    max_rating:float = Query(default=None, alias="maxRating"),
    limit:int = Query(default=20, ge=1, le=100),
    skip:int = Query(default=0, ge=0),
    sort_by:str = Query(default="title", alias="sortBy"),
    sort_order:str = Query(default="asc", alias="sortOrder")
):
    movies_collection = get_collection("movies")
    filter_dict = {}
    if q:
        filter_dict["$text"] = {"$search": q}
    if title:
        filter_dict["title"] = {"$regex": title, "$options": "i"}
    if genre:
        filter_dict["genres"] = {"$regex": genre, "$options": "i"}
    if isinstance(year, int):
        filter_dict["year"] = year
    if min_rating is not None or max_rating is not None:
        rating_filter = {}
        if min_rating is not None:
            rating_filter["$gte"] = min_rating
        if max_rating is not None:
            rating_filter["$lte"] = max_rating
        filter_dict["imdb.rating"] = rating_filter

    # Building the sort object based on user input
    sort_order = -1 if sort_order == "desc" else 1

    sort = [(sort_by, sort_order)]

    # Query the database with the constructed filter, sort, skip, and limit.

    try:
        result = movies_collection.find(filter_dict).sort(sort).skip(skip).limit(limit)
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"An error occurred while fetching movies. {str(e)}"
        )

    movies = []

    async for movie in result:
        if "title" in movie:
            movie["_id"] = str(movie["_id"]) # Convert ObjectId to string
            # Ensure that the year field contains int value.
            if "year" in movie and not isinstance(movie["year"], int):
                cleaned_year = re.sub(r"\D", "", str(movie["year"]))
                try:
                    movie["year"] = int(cleaned_year) if cleaned_year else None
                except ValueError:
                    movie["year"] = None
            
            movies.append(movie)

    # Return the results wrapped in a SuccessResponse
    message = f"Found {len(movies)} movies."
    return create_success_response(movies, message)

"""
    POST /api/movies/
    Create a new movie.
    Request Body:
        movie (CreateMovieRequest): A movie object containing the movie data.
            See CreateMovieRequest model for available fields.
    Returns:
        SuccessResponse[Movie]: A response object containing the created movie data.
"""

@router.post("/",
            response_model=SuccessResponse[Movie],
            status_code = 201,
            summary="Creates a new movie in the database.")
async def create_movie(movie: CreateMovieRequest):
    # Pydantic automatically validates the structure
    movie_data = movie.model_dump(by_alias=True, exclude_none=True)

    movies_collection = get_collection("movies")
    try:
        result = await movies_collection.insert_one(movie_data)
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"Database error occurred: {str(e)}"
        )

    # Verify that the document was created before querying it
    if not result.acknowledged:
        raise HTTPException(
            status_code = 500,
            detail="Failed to create movie: The database did not acknowledge the insert operation"
        )

    try:
        # Retrieve the created document to return complete data
        created_movie = await movies_collection.find_one({"_id": result.inserted_id})
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"Database error occurred: {str(e)}"
        )

    if created_movie is None:
        raise HTTPException(
            status_code = 500,
            detail="Movie was created but could not be retrieved for verification"
        )

    created_movie["_id"] = str(created_movie["_id"]) # Convert ObjectId to string

    return create_success_response(created_movie, f"Movie '{movie_data['title']}' created successfully")

"""
POST /api/movies/batch

Create multiple movies in a single request.

Request Body:
        movies (List[CreateMovieRequest]): A list of movie objects to insert. Each object should include:
            - title (str): The movie title.
            - year (int, optional): The release year.
            - plot (str, optional): Short plot summary.
            - fullplot (str, optional): Full plot summary.
            - genres (List[str], optional): List of genres.
            - directors (List[str], optional): List of directors.
            - writers (List[str], optional): List of writers.
            - cast (List[str], optional): List of cast members.
            - countries (List[str], optional): List of countries.
            - languages (List[str], optional): List of languages.
            - rated (str, optional): Movie rating.
            - runtime (int, optional): Runtime in minutes.
            - poster (str, optional): Poster URL.

    Returns:
        SuccessResponse: A response object containing the number of inserted movies and their IDs.

"""

@router.post(
        "/batch",
        response_model=SuccessResponse[dict],
        status_code = 201,
        summary = "Create multiple movies in a single request."
        )
async def create_movies_batch(movies: List[CreateMovieRequest]) ->SuccessResponse[dict]:
    movies_collection = get_collection("movies")

    #Verify that the movies list is not empty
    if not movies:
        raise HTTPException(
            status_code = 400,
            detail="Request body must be a non-empty list of movies."
        )

    movies_dicts = []

    for movie in movies:
        movie_dict = movie.model_dump(exclude_unset=True, exclude_none=True)
        # Remove _id if it exists to let MongoDB generate it automatically
        movie_dict.pop('_id', None)
        movies_dicts.append(movie_dict)

    try:
        result = await movies_collection.insert_many(movies_dicts)
        return create_success_response({
            "insertedCount": len(result.inserted_ids),
            "insertedIds": [str(_id) for _id in result.inserted_ids]
            },
            f"Successfully created {len(result.inserted_ids)} movies."
        )
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"Database error occurred: {str(e)}"
        )

"""
    PATCH /api/movies/{id}

    Update a single movie by its ID.

    Path Parameters:
        id (str): The ObjectId of the movie to update

    Request Body:
        move_data (UpdateMovieRequest): Fields and values to update. Only provided fields will be updated.

    Returns:
        SuccessResponse: The updated movie document, the number of fields modified and a success message.
"""
@router.patch(
        "/{id}",
        response_model=SuccessResponse[Movie],
        status_code = 200,
        summary="Update a single movie by its ID.")
async def update_movie(
    movie_data: UpdateMovieRequest,
    movie_id: str = Path(..., alias="id")
) -> SuccessResponse[Movie]:

    movies_collection = get_collection("movies")

    # Validate the ObjectId
    try:
        movie_id = ObjectId(movie_id)
    except Exception :
        raise HTTPException(
            status_code = 400,
            detail=f"Invalid movie_id format: {movie_id}"
        )

    update_dict = movie_data.model_dump(exclude_unset=True, exclude_none=True)

    # Validate that the dict is not empty
    if not update_dict:
        raise HTTPException(
            status_code = 400,
            detail="No valid fields provided for update."
        )

    try:
        result = await movies_collection.update_one(
            {"_id": movie_id},
            {"$set":update_dict}
        )
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"An error occurred while updating the movie: {str(e)}"
        )

    if result.matched_count == 0:
        raise HTTPException(
            status_code = 404,
            detail=f"No movie with that _id was found: {movie_id}"
        )

    updatedMovie = await movies_collection.find_one({"_id": movie_id})
    updatedMovie["_id"] = str(updatedMovie["_id"])

    return create_success_response(updatedMovie, f"Movie updated successfully. Modified {len(update_dict)} fields.")

"""
    PATCH /api/movies

    Batch update movies matching the given filter

    Request Body:
        filter (MoviesUpdateFilter): Criteria to select which movies to update. Only movies matching this filter will be updated.
        update (UpdateMovieRequest): Fields and values to update for the matched movies. Only provided fields will be updated.
    Returns:
        SuccessResponse: A response object containing the number of matched and modified movies and a success message.
"""

@router.patch("/",
        response_model=SuccessResponse[dict],
        status_code = 200,
        summary="Batch update movies matching the given filter."
        )
async def update_movies_batch(
    request_body: dict = Body(...)
) -> SuccessResponse[dict]:
    movies_collection = get_collection("movies")

    # Extract filter and update from the request body
    filter_data = request_body.get("filter", {})
    update_data = request_body.get("update", {})

    if not filter_data or not update_data:
        raise HTTPException(
            status_code = 400,
            detail="Both filter and update objects are required"
        )

    # Convert string IDs to ObjectIds if _id filter is present
    if "_id" in filter_data and isinstance(filter_data["_id"], dict):
        if "$in" in filter_data["_id"]:
            # Convert list of string IDs to ObjectIds
            try:
                filter_data["_id"]["$in"] = [ObjectId(id_str) for id_str in filter_data["_id"]["$in"]]
            except Exception:
                raise HTTPException(
                    status_code = 400,
                    detail="Invalid ObjectId format in filter",
                )

    try:
        result = await movies_collection.update_many(filter_data, {"$set": update_data})
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"An error occurred while updating movies: {str(e)}"
        )

    return create_success_response({
        "matchedCount": result.matched_count,
        "modifiedCount": result.modified_count
        },
        f"Update operation completed. Matched {result.matched_count} movie(s), modified {result.modified_count} movie(s)."
)

"""
    DELETE /api/movies/{id}
    Delete a single movie by its ID.
    Path Parameters:
        id (str): The ObjectId of the movie to delete.
    Returns:
        SuccessResponse[dict]: A response object containing deletion details.
"""

@router.delete("/{id}",
                response_model=SuccessResponse[dict],
                status_code = 200,
                summary="Delete a single movie by its ID.")
async def delete_movie_by_id(id: str):
    try:
        object_id = ObjectId(id)
    except errors.InvalidId:
        raise HTTPException(
            status_code = 400,
            detail=f"Invalid movie ID format: The provided ID '{id}' is not a valid ObjectId"
        )

    movies_collection = get_collection("movies")
    try:
        # Use deleteOne() to remove a single document
        result = await movies_collection.delete_one({"_id": object_id})
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"Database error occurred: {str(e)}"
        )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code = 404,
            detail=f"No movie found with ID: {id}"
        )

    return create_success_response(
        {"deletedCount": result.deleted_count},
        "Movie deleted successfully"
    )

"""
    DELETE /api/movies/

    Delete multiple movies matching the given filter.

    Request Body:
        movie_filter (MovieFilter): Criteria to select which movies to delete. Only movies matching this filter will be removed.

        Returns:
        SuccessResponse: An object containing the number of deleted movies and a success message.
"""

@router.delete(
        "/",
        response_model=SuccessResponse[dict],
        status_code = 200,
        summary="Delete multiple movies matching the given filter."
)
async def delete_movies_batch(request_body: dict = Body(...)) -> SuccessResponse[dict]:

    movies_collection = get_collection("movies")

    # Extract filter from the request body
    filter_data = request_body.get("filter", {})

    if not filter_data:
        raise HTTPException(
            status_code = 400,
            detail="Filter object is required and cannot be empty."
        )

    # Convert string IDs to ObjectIds if _id filter is present
    if "_id" in filter_data and isinstance(filter_data["_id"], dict):
        if "$in" in filter_data["_id"]:
            # Convert list of string IDs to ObjectIds
            try:
                filter_data["_id"]["$in"] = [ObjectId(id_str) for id_str in filter_data["_id"]["$in"]]
            except Exception:
                raise HTTPException(
                    status_code = 400,
                    detail="Invalid ObjectId format in filter."
                )

    try:
        result = await movies_collection.delete_many(filter_data)
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"An error occurred while deleting movies: {str(e)}"
        )

    return create_success_response(
        {"deletedCount":result.deleted_count},
        f'Delete operation completed. Removed {result.deleted_count} movies.'
    )

"""
    DELETE /api/movies/{id}/find-and-delete
    Finds and deletes a movie in a single atomic operation.
    Demonstrates the findOneAndDelete() operation.
    Path Parameters:
        id (str): The ObjectId of the movie to find and delete.
    Returns:
        SuccessResponse[Movie]: A response object containing the deleted movie data.
"""

@router.delete("/{id}/find-and-delete",
                response_model=SuccessResponse[Movie],
                status_code = 200,
                summary="Find and delete a movie in a single operation.")
async def find_and_delete_movie(id: str):
    try:
        object_id = ObjectId(id)
    except errors.InvalidId:
        raise HTTPException(
            status_code = 400,
            detail=f"Invalid movie ID format: The provided ID '{id}' is not a valid ObjectId"
        )

    movies_collection = get_collection("movies")
    # Use find_one_and_delete() to find and delete in a single atomic operation
    # This is useful when you need to return the deleted document
    # or ensure the document exists before deletion
    try:
        deleted_movie = await movies_collection.find_one_and_delete({"_id": object_id})
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"Database error occurred: {str(e)}"
        )

    if deleted_movie is None:
        raise HTTPException(
            status_code = 404,
            detail=f"No movie found with ID: {id}"
        )
    deleted_movie["_id"] = str(deleted_movie["_id"]) # Convert ObjectId to string

    return create_success_response(deleted_movie, "Movie found and deleted successfully")

"""
    GET /api/movies/aggregations/reportingByComments
    Aggregate movies with their most recent comments using MongoDB $lookup aggregation.
    Joins movies with comments collection to show recent comment activity.
    Query Parameters:
        limit (int, optional): Number of results to return (default: 10, max: 50).
        movie_id (str, optional): Filter by specific movie ObjectId.
    Returns:
        SuccessResponse[List[dict]]: A response object containing movies with their most recent comments.
"""

@router.get("/aggregations/reportingByComments",
            response_model=SuccessResponse[List[dict]],
            status_code = 200,
            summary="Aggregate movies with their most recent comments.")
async def aggregate_movies_recent_commented(
    limit: int = Query(default=10, ge=1, le=50),
    movie_id: str = Query(default=None)
):

    # Add a multi-stage aggregation that:
    # 1. Filters movies by valid year range
    # 2. Joins with comments collection (like SQL JOIN)
    # 3. Filters to only movies that have comments
    # 4. Sorts comments by date and extracts most recent ones
    # 5. Sorts movies by their most recent comment date
    # 6. Shapes the final output with transformed comment structure

    pipeline: list[dict[str, Any]] =[
        # STAGE 1: $match - Initial Filter
        # Filter movies to only those with valid year data
        {
            "$match": {
                "year": {"$type": "number"}
            }
        }
    ]

    # Add movie_id filter if provided
    if movie_id:
        try:
            object_id = ObjectId(movie_id)
            pipeline[0]["$match"]["_id"] = object_id
        except Exception:
            raise HTTPException(
                status_code = 400,
                detail="The provided movie_id is not a valid ObjectId"
            )

    # Add remaining pipeline stages
    pipeline.extend([
        # STAGE 2: $lookup - Join with the 'comments' Collection
        # This gives each movie document a 'comments' array containing all its comments
        {
            "$lookup": {
                "from": "comments",
                "localField": "_id",
                "foreignField": "movie_id",
                "as": "comments"
            }
        },
        # STAGE 3: $match - Filter Movies with at Least One Comment
        # This helps reduces dataset to only movies with user engagement
        {
            "$match": {
                "comments": {"$ne": []}
            }
        },
        # STAGE 4: $addFields - Add New Computed Fields
        {
            "$addFields": {
                # Add computed field 'recentComments' that extracts only the N most recent comments (up to 'limit')
                "recentComments": {
                    "$slice": [
                        {
                            "$sortArray": {
                                "input": "$comments",
                                "sortBy": {"date": -1}  # -1 = descending (newest first)
                            }
                        },
                        limit  # Number of comments to keep
                    ]
                },
                # Add computed field 'mostRecentCommentDate' that gets the date of the most recent comment (to use in the next $sort stage)
                "mostRecentCommentDate": {
                    "$max": "$comments.date"
                }
            }
        },
        # STAGE 5: $sort - Sort Movies by Most Recent Comment Date
        {
            "$sort": {"mostRecentCommentDate": -1}
        },
        # STAGE 6: $limit - Restrict Result Set Size
        # - If querying single movie: return up to 50 results
        # - If querying all movies: return up to 20 results
        # Tip: This prevents overwhelming the client with too much data
        {
            "$limit": 50 if movie_id else 20
        },
        # STAGE 7: $project - Shape Final Response Output
        {
            "$project": {
                # Include basic movie fields
                "title": 1,
                "year": 1,
                "genres": 1,
                "_id": 1,
                # Extract nested field: imdb.rating -> imdbRating
                "imdbRating": "$imdb.rating",
                # Use $map to reshape computed 'recentComments' field with cleaner field names
                "recentComments": {
                    "$map": {
                        "input": "$recentComments",
                        "as": "comment",
                        "in": {
                            "userName": "$$comment.name",      # Rename: name -> userName
                            "userEmail": "$$comment.email",    # Rename: email -> userEmail
                            "text": "$$comment.text",          # Keep: text
                            "date": "$$comment.date"           # Keep: date
                        }
                    }
                },
                # Calculate the total number of comments into 'totalComments' (not just 'recentComments')
                # Used in display (e.g., "Showing 5 of 127 comments")
                "totalComments": {"$size": "$comments"}
            }
        }
    ])
    # Execute the aggregation
    try:
        results = await execute_aggregation(pipeline)
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"Database error occurred during aggregation: {str(e)}"
        )

    # Convert ObjectId to string for response
    for result in results:
        if "_id" in result:
            result["_id"] = str(result["_id"])

    # Calculate total comments from all movies
    total_comments = sum(result.get("totalComments", 0) for result in results)

    return create_success_response(
        results,
        f"Found {total_comments} comments from movie{'s' if len(results) != 1 else ''}"
    )

"""
    GET /api/movies/aggregations/reportingByYear
    Aggregate movies by year with average rating and movie count.
    Reports yearly statistics including average rating and total movies per year.
    Returns:
        SuccessResponse[List[dict]]: A response object containing yearly movie statistics.
"""

@router.get("/aggregations/reportingByYear",
            response_model=SuccessResponse[List[dict]],
            status_code = 200,
            summary="Aggregate movies by year with average rating and movie count.")
async def aggregate_movies_by_year():
    # Define aggregation pipeline to group movies by year with statistics
    # This pipeline demonstrates grouping, statistical calculations, and data cleaning

    # Add a multi-stage aggregation that:
    # 1. Filters movies by valid year range (data quality filter)
    # 2. Groups movies by release year and calculates statistics per year
    # 3. Shapes the final output with clean field names and rounded averages
    # 4. Sorts results by year (newest first) for chronological presentation

    pipeline = [
        # STAGE 1: $match - Data Quality Filter
        # Clean data: ensure year is an integer and within reasonable range
        # Tip: Filter early to reduce dataset size and improve performance
        {
            "$match": {
                "year": {"$type": "number"}
            }
        },

        # STAGE 2: $group - Aggregate Movies by Year
        # Group all movies by their release year and calculate various statistics
        {
            "$group": {
                "_id": "$year",  # Group by year field
                "movieCount": {"$sum": 1},  # Count total movies per year

                # Calculate average rating (only for valid numeric ratings)
                "averageRating": {
                    "$avg": {
                        "$cond": [
                            {"$and": [
                                {"$ne": ["$imdb.rating", None]},           # Not null
                                {"$ne": ["$imdb.rating", ""]},             # Not empty string
                                {"$eq": [{"$type": "$imdb.rating"}, "double"]}  # Is numeric
                            ]},
                            "$imdb.rating",  # Include valid IMDB ratings
                            "$$REMOVE"       # Exclude invalid IMDB ratings
                        ]
                    }
                },

                # Find highest rating for the year (same validation as average rating)
                "highestRating": {
                    "$max": {
                        "$cond": [
                            {"$and": [
                                {"$ne": ["$imdb.rating", None]},
                                {"$ne": ["$imdb.rating", ""]},
                                {"$eq": [{"$type": "$imdb.rating"}, "double"]}
                            ]},
                            "$imdb.rating",
                            "$$REMOVE"
                        ]
                    }
                },

                # Find lowest rating for the year (same validation as average and highest rating)
                "lowestRating": {
                    "$min": {
                        "$cond": [
                            {"$and": [
                                {"$ne": ["$imdb.rating", None]},
                                {"$ne": ["$imdb.rating", ""]},
                                {"$eq": [{"$type": "$imdb.rating"}, "double"]}
                            ]},
                            "$imdb.rating",
                            "$$REMOVE"
                        ]
                    }
                },

                # Sum total votes across all movies in the year
                "totalVotes": {"$sum": "$imdb.votes"}
            }
        },

        # STAGE 3: $project - Shape Final Output
        # Transform the grouped data into a clean, readable format
        {
            "$project": {
                "year": "$_id",  # Rename _id back to year because grouping was done by year but values were stored in _id
                "movieCount": 1,
                "averageRating": {"$round": ["$averageRating", 2]},  # Round to 2 decimal places
                "highestRating": 1,
                "lowestRating": 1,
                "totalVotes": 1,
                "_id": 0  # Exclude the _id field from output
            }
        },

        # STAGE 4: $sort - Sort by Year (Newest First)
        # Sort results in descending order to show most recent years first
        {"$sort": {"year": -1}}  # -1 = descending order
    ]

    # Execute the aggregation
    try:
        results = await execute_aggregation(pipeline)
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"Database error occurred during aggregation: {str(e)}"
        )

    return create_success_response(
        results,
        f"Aggregated statistics for {len(results)} years"
    )

"""
    GET /api/movies/aggregations/reportingByDirectors
    Aggregate directors with the most movies and their statistics.
    Reports directors sorted by number of movies directed.
    Query Parameters:
        limit (int, optional): Number of results to return (default: 20, max: 100).
    Returns:
        SuccessResponse[List[dict]]: A response object containing director statistics.
"""

@router.get("/aggregations/reportingByDirectors",
            response_model=SuccessResponse[List[dict]],
            status_code = 200,
            summary="Aggregate directors with the most movies and their statistics.")
async def aggregate_directors_most_movies(
    limit: int = Query(default=20, ge=1, le=100)
):
    # Define aggregation pipeline to find directors with the most movies
    # This pipeline demonstrates array unwinding, filtering, and ranking

    # Add a multi-stage aggregation that:
    # 1. Filters movies with valid directors and year data (data quality filter)
    # 2. Unwinds directors array to create separate documents per director
    # 3. Cleans director names by filtering out null/empty names
    # 4. Groups movies by individual director and calculates statistics per director
    # 5. Sorts directors based on movie count
    # 6. Limits results to top N directors
    # 7. Shapes the final output with clean field names and rounded averages

    pipeline = [
        # STAGE 1: $match - Initial Data Quality Filter
        # Filter movies that have director information and valid years
        {
            "$match": {
                "directors": {"$exists": True, "$ne": None, "$ne": []},  # Has directors array
                "year": {"$type": "number"}  # Valid year (numeric)
            }
        },

        # STAGE 2: $unwind - Flatten Directors Array
        # Convert each movie's directors array into separate documents
        # Example: Movie with ["Director A", "Director B"] becomes 2 documents
        {
            "$unwind": "$directors"
        },

        # STAGE 3: $match - Clean Director Names
        # Filter out any null or empty director names after unwinding
        {
            "$match": {
                "directors": {"$ne": None, "$ne": ""}
            }
        },

        # STAGE 4: $group - Aggregate by Director
        # Group all movies by director name and calculate statistics
        {
            "$group": {
                "_id": "$directors",  # Group by individual director name
                "movieCount": {"$sum": 1},  # Count movies per director
                "averageRating": {"$avg": "$imdb.rating"}  # Average rating of director's movies
            }
        },

        # STAGE 5: $sort - Rank Directors by Movie Count
        # Sort directors by number of movies (highest first)
        {"$sort": {"movieCount": -1}},  # -1 = descending (most movies first)

        # STAGE 6: $limit - Restrict Results
        # Limit to top N directors based on user input
        {"$limit": limit},

        # STAGE 7: $project - Shape Final Output
        # Transform the grouped data into a clean, readable format
        {
            "$project": {
                "director": "$_id",  # Rename _id to director
                "movieCount": 1,
                "averageRating": {"$round": ["$averageRating", 2]},  # Round to 2 decimal places
                "_id": 0  # Exclude the _id field from output
            }
        }
    ]

    # Execute the aggregation
    try:
        results = await execute_aggregation(pipeline)
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail=f"Database error occurred during aggregation: {str(e)}"
        )

    return create_success_response(
        results,
        f"Found {len(results)} directors with most movies"
    )

#------------------------------------
#Helper Functions
#------------------------------------

"""
    Helper function to execute aggregation pipeline and return results.

    Args:
        pipeline: MongoDB aggregation pipeline stages

    Returns:
        List of documents from aggregation result
"""

async def execute_aggregation(pipeline: list) -> list:
    """Helper function to execute aggregation pipeline and return results"""

    movies_collection = get_collection("movies")
    # For the async Pymongo driver, we need to await the aggregate call
    cursor = await movies_collection.aggregate(pipeline)
    results = await cursor.to_list(length=None)  # Convert cursor to list to collect all data at once rather than processing data per document

    return results

"""
    Helper function to execute aggregation pipeline and return results from a specified collection.

    Args:
        collection: The MongoDB collection to run the aggregation on
        pipeline: MongoDB aggregation pipeline stages

    Returns:
        List of documents from aggregation result
"""

async def execute_aggregation_on_collection(collection, pipeline: list) -> list:
    """Helper function to execute aggregation pipeline on a specified collection and return results"""

    cursor = await collection.aggregate(pipeline)
    results = await cursor.to_list(length=None)  # Convert cursor to list

    return results

"""
    Helper function to generate vector embeddings from an input.

    Args:
        data: Input data to generate embeddings for
        input_type: Type of input data
        client: Voyage AI client instance

    Returns:
        Vector embeddings for the given input
"""

def get_embedding(data, input_type = "document", client=None):
    """
    Helper function to generate vector embeddings from an input.

    Args:
        data: Input data to generate embeddings for
        input_type: Type of input data
        client: Voyage AI client instance

    Returns:
        Vector embeddings for the given input

    Raises:
        VoyageAuthError: If the API key is invalid (401)
        VoyageAPIError: For other API errors
    """
    try:
        if client is None:
            client = voyageai.Client()

        embeddings = client.embed(
            data, model = model, output_dimension = outputDimension, input_type = input_type
        ).embeddings
        return embeddings[0]
    except voyage_error.AuthenticationError as e:
        # Handle authentication errors (401) from Voyage AI SDK
        raise VoyageAuthError("Invalid Voyage AI API key. Please check your VOYAGE_API_KEY in the .env file")
    except voyage_error.InvalidRequestError as e:
        # Handle invalid request errors (400) - often due to malformed API key
        raise VoyageAPIError(f"Invalid request to Voyage AI API: {str(e)}", 400)
    except voyage_error.RateLimitError as e:
        # Handle rate limiting errors (429)
        raise VoyageAPIError(f"Voyage AI API rate limit exceeded: {str(e)}", 429)
    except voyage_error.ServiceUnavailableError as e:
        # Handle service unavailable errors (502, 503, 504)
        raise VoyageAPIError(f"Voyage AI service unavailable: {str(e)}", 503)
    except voyage_error.VoyageError as e:
        # Handle any other Voyage AI SDK errors
        raise VoyageAPIError(f"Voyage AI API error: {str(e)}", getattr(e, 'http_status', 500) or 500)
    except Exception as e:
        # Handle unexpected errors
        raise VoyageAPIError(f"Failed to generate embedding: {str(e)}", 500)

