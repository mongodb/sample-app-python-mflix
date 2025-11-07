from fastapi import Request
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError, DuplicateKeyError, WriteError
from datetime import datetime, timezone
from typing import Any, Optional
from src.models.models import ErrorDetails, ErrorResponse, SuccessResponse, T

'''
Creates a standardized success response.


Args:
    data (T): The data to include in the response.
    message (Optional[str]): An optional message to include.

Returns:
    SuccessResponse[T]: A standardized success response object.
    '''

def create_success_response(data:T, message: Optional[str] = None) -> SuccessResponse[T]:
    return SuccessResponse(
        message=message or "Operation completed successfully.",
        data=data,
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
        
    )

'''
Creates a standardized error response.

Args:
    message (str): The error message.
    code (Optional[str]): An optional error code.
    details (Optional[Any]): Additional error details.

Returns:
    ErrorResponse: A standardized error response object.     

'''

def create_error_response(message: str, code: Optional[str]=None, details: Optional[Any]=None) -> ErrorResponse:
    return ErrorResponse(
        message=message,
        error=ErrorDetails(
            message=message,
            code=code,
            details=details
        ),
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
    )


def parse_mongo_exception(exc: Exception) -> dict:
    if isinstance(exc, DuplicateKeyError):
        return{
            "message": "Duplicate key error occurred.",
            "code": "DUPLICATE_KEY_ERROR",
            "details": "A document with the same key already exists.",
            "statusCode":409
        }
        
        # This is stating that the data that you are trying to implement is the wrong shape
        # for the schema implemented in MongoDB.
    elif isinstance(exc, WriteError):
        return{
            "message": "Document validation failed.",
            "code": "WRITE_ERROR",
            "details": str(exc),
            "statusCode":400
        }
        
    elif isinstance(exc, PyMongoError):
        return {
            "message" : "A database error occurred.",
            "code": "DATABASE_ERROR",
            "details": str(exc),
            "statusCode":500
        }
    return {
        "message": "An unknown error occurred.",
        "code": "UNKNOWN_ERROR",
        "details": str(exc),
        "statusCode": 500
    }

def register_error_handlers(app):

    @app.exception_handler(PyMongoError)
    async def mongo_exception_handler(request: Request, exc: PyMongoError):
        error_details = parse_mongo_exception(exc)
        return JSONResponse(
            status_code = error_details["statusCode"],
            content=create_error_response(
                message=error_details["message"],
                code=error_details["code"],
                details=error_details["details"]
            ).model_dump()
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message=str(exc),
                code="INTERNAL_SERVER_ERROR",
                details=getattr(exc, 'detail', None) or getattr(exc, 'args', None)
            ).model_dump()
        )
