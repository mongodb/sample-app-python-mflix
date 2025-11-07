from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import movies
from src.utils.errorHandler import register_error_handlers
from src.database.mongo_client import db, get_collection

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create search indexes
    await ensure_search_index()
    await vector_search_index()

    # Print server information
    print(f"\n{'='*60}")
    print(f"  Server started at http://127.0.0.1:3001")
    print(f"  Documentation at http://127.0.0.1:3001/docs")
    print(f"  Interactive API docs at http://127.0.0.1:3001/redoc")
    print(f"{'='*60}\n")

    yield
    # Shutdown: Clean up resources if needed
    # Add any cleanup code here


async def ensure_search_index():
    try:
        movies_collection = db.get_collection("movies")
        comments_collection = db.get_collection("comments")
        
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


async def vector_search_index():
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


app = FastAPI(lifespan=lifespan)

# Add CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],  # Load from environment variable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(movies.router, prefix="/api/movies", tags=["movies"])

