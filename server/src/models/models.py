from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, TypeVar, Generic, Any


T = TypeVar("T")

class Awards(BaseModel):
    wins: Optional[int] = None
    nominations: Optional[int] = None
    text: Optional[str] = None

class Imdb(BaseModel):
    rating: Optional[float] = None
    votes: Optional[int] = None
    id: Optional[int] = None    

class Movie(BaseModel):
    id: Optional[str] = Field(alias="_id")
    title: str
    year: Optional[int] = None
    plot: Optional[str]  = None
    fullplot: Optional[str] = None
    released: Optional[datetime]  = None
    runtime: Optional[int]  = None
    poster: Optional[str]  = None
    genres: Optional[list[str]]  = None
    directors: Optional[list[str]]  = None
    writers: Optional[list[str]]  = None
    cast: Optional[list[str]]  = None
    countries: Optional[list[str]]  = None
    languages: Optional[list[str]]  = None
    rated: Optional[str]  = None
    awards: Optional[Awards] = None
    imdb: Optional[Imdb] = None

    model_config = {
        "populate_by_name" : True
    }

class TextFilter(BaseModel):
    search: str = Field(..., alias="$search")

class RegexFilter(BaseModel):
    regex: str = Field(..., alias="$regex")
    options: Optional[str] = Field(None, alias="$options")    

class RatingFilter(BaseModel):
    gte: Optional[float] = Field(None, alias="$gte")
    lte: Optional[float] = Field(None, alias="$lte")    

class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    pages: int

class CreateMovieRequest(BaseModel):
    title: str
    year: Optional[int] = None
    plot: Optional[str]  = None
    fullplot: Optional[str] = None
    genres: Optional[list[str]]  = None
    directors: Optional[list[str]]  = None
    writers: Optional[list[str]]  = None
    cast: Optional[list[str]]  = None
    countries: Optional[list[str]]  = None
    languages: Optional[list[str]]  = None
    rated: Optional[str]  = None
    runtime: Optional[int]  = None
    poster: Optional[str]  = None    

class UpdateMovieRequest(BaseModel):
    title: Optional[str] = None
    year: Optional[int] = None
    plot: Optional[str]  = None
    fullplot: Optional[str] = None
    genres: Optional[list[str]]  = None
    directors: Optional[list[str]]  = None
    writers: Optional[list[str]]  = None
    cast: Optional[list[str]]  = None
    countries: Optional[list[str]]  = None
    languages: Optional[list[str]]  = None
    rated: Optional[str]  = None
    runtime: Optional[int]  = None
    poster: Optional[str]  = None  

class MovieFilter(BaseModel):
    _id: Optional[Any] = None  # Support for MongoDB ID queries like { $in: [...] }
    title: Optional[str] = None
    year: Optional[int] = None
    plot: Optional[str]  = None
    fullplot: Optional[str] = None
    genres: Optional[list[str]]  = None
    directors: Optional[list[str]]  = None
    writers: Optional[list[str]]  = None
    cast: Optional[list[str]]  = None
    countries: Optional[list[str]]  = None
    languages: Optional[list[str]]  = None
    rated: Optional[str]  = None
    runtime: Optional[int]  = None
    poster: Optional[str]  = None   

class SearchMoviesResponse(BaseModel):
    movies: list[Movie]
    totalCount: int
      
class VectorSearchResult(BaseModel):
    id: Optional[str] = Field(alias="_id")
    title: str
    plot: Optional[str] = None
    poster: Optional[str] = None
    year: Optional[int] = None
    genres: Optional[list[str]] = None
    directors: Optional[list[str]] = None
    cast: Optional[list[str]] = None
    score: float

    model_config = {
        "populate_by_name": True
    }

class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str]
    data: T
    timestamp: str
    pagination: Optional[Pagination] = None


class ErrorDetails(BaseModel):
    message: str
    code: Optional[str]
    details: Optional[Any] = None

class BatchUpdateRequest(BaseModel):
    filter: MovieFilter
    update: UpdateMovieRequest

class BatchDeleteRequest(BaseModel):
    filter: MovieFilter

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error: ErrorDetails
    timestamp: str
    