from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.routers import movies
from src.database.mongo_client import db, get_collection
from src.utils.exceptions import VoyageAuthError, VoyageAPIError
from src.utils.errorResponse import create_error_response
from src.utils.logger import logger
from src.middleware.request_logging import RequestLoggingMiddleware

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create search indexes
    await ensure_mongodb_search_index()
    await ensure_vector_search_index()
    await ensure_standard_index()

    # Log server information
    logger.info("=" * 60)
    logger.info("  Server started at http://127.0.0.1:3001")
    logger.info("  Documentation at http://127.0.0.1:3001/docs")
    logger.info("  Interactive API docs at http://127.0.0.1:3001/redoc")
    logger.info("=" * 60)

    yield
    # Shutdown: Clean up resources if needed
    # Add any cleanup code here


async def ensure_mongodb_search_index():
    try:
        movies_collection = db.get_collection("movies")
        
        # Check and create search index for movies collection
        result = await movies_collection.list_search_indexes()
        indexes = [idx async for idx in result]
        index_names = [index["name"] for index in indexes]
        if "movieSearchIndex" in index_names:
            return

        # Create a mapping if the movieSearchIndex does not exist
        index_definition = {
            "mappings": {
                "dynamic": False,
                "fields": {
                    "plot": {"type": "string", "analyzer": "lucene.standard"},
                    "fullplot": {"type": "string", "analyzer": "lucene.standard"},
                    "directors": {"type": "string", "analyzer": "lucene.standard"},
                    "writers": {"type": "string", "analyzer": "lucene.standard"},
                    "cast": {"type": "string", "analyzer": "lucene.standard"}
                }
            }
        }
        # Creates movieSearchIndex on the movies collection
        await db.command({
            "createSearchIndexes": "movies",
            "indexes": [{
                "name": "movieSearchIndex",
                "definition": index_definition
            }]
        })
    except Exception as e:
        raise RuntimeError(
            f"Failed to create search index 'movieSearchIndex': {str(e)}. "
            f"Search functionality may not work properly. "
            f"Please check your MongoDB Atlas configuration and ensure the cluster supports search indexes."
        )


async def ensure_vector_search_index():
    """
    Creates vector search index on application startup if it doesn't already exist.
    This ensures the index is ready before any vector search requests are made.
    """
    try:
        embedded_movies_collection = get_collection("embedded_movies")
        
        # Get list of existing indexes - convert AsyncCommandCursor to list
        existing_indexes_cursor = await embedded_movies_collection.list_search_indexes()
        existing_indexes = await existing_indexes_cursor.to_list(length=None)
        index_names = [index.get("name") for index in existing_indexes]
        
        # Check if our vector_index already exists
        if "vector_index" not in index_names:
            
            # Define the vector search index specification
            index_definition = {
                "name": "vector_index",
                "type": "vectorSearch",
                "definition": {
                    "fields": [
                        {
                            "type": "vector",
                            "path": "plot_embedding_voyage_3_large",
                            "numDimensions": 2048, #Set this to 2048 to match the embedding dimensions on the path
                            "similarity": "cosine"
                        }
                    ]
                }
            }
            
            # Create the index
            await embedded_movies_collection.create_search_index(index_definition)
            
    except Exception as e:
        raise RuntimeError(
            f"Failed to create vector search index 'vector_index': {str(e)}. "
            f"Vector search functionality will not be available. "
            f"Please check your MongoDB Atlas configuration, ensure the cluster supports vector search, "
            f"and verify the 'embedded_movies' collection exists with the required embedding field."
        )

async def ensure_standard_index():
    """
    Creates a standard MongoDB index on the comments collection on application startup.
    This improves performance for queries filtering by movie_id such as ReportingByComments().
    """

    try:
        comments_collection = db.get_collection("comments")

        existing_indexes_cursor = await comments_collection.list_indexes()
        existing_indexes = [index async for index in existing_indexes_cursor]
        index_names = [index.get("name") for index in existing_indexes]
        standard_index_name = "movie_id_index"
        if standard_index_name not in index_names:
            await comments_collection.create_index([("movie_id", 1)], name=standard_index_name)

    except Exception as e:
        logger.warning(f"Failed to create standard index on 'comments' collection: {str(e)}")
        logger.warning("Performance may be degraded. Please check your MongoDB configuration.")


app = FastAPI(lifespan=lifespan)

# Add custom exception handlers
@app.exception_handler(VoyageAuthError)
async def voyage_auth_error_handler(request: Request, exc: VoyageAuthError):
    """Handle Voyage AI authentication errors with 401 status."""
    return JSONResponse(
        status_code=401,
        content=create_error_response(
            message=exc.message,
            code="VOYAGE_AUTH_ERROR",
            details="Please verify your VOYAGE_API_KEY is correct in the .env file"
        )
    )

@app.exception_handler(VoyageAPIError)
async def voyage_api_error_handler(request: Request, exc: VoyageAPIError):
    """Handle Voyage AI API errors with 503 status."""
    return JSONResponse(
        status_code=503,
        content=create_error_response(
            message="Vector search service unavailable",
            code="VOYAGE_API_ERROR",
            details=exc.message
        )
    )

# Add CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],  # Load from environment variable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

app.include_router(movies.router, prefix="/api/movies", tags=["movies"])

