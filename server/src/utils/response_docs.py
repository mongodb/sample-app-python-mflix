"""
OpenAPI Response Documentation Helpers

This module provides reusable response documentation for FastAPI endpoints
to maintain consistent OpenAPI documentation across all movie API endpoints.
Uses the standardized error format from create_error_response() to match Express backend.
"""


# Helper schema for standardized error responses (matches create_error_response format)
ERROR_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        "error": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "code": {"type": "string"},
                "details": {"type": "string"}
            }
        },
        "timestamp": {"type": "string"}
    }
}


# 400 Bad Request Responses
ERROR_400_INVALID_OBJECTID = {
    "description": "Bad Request - Invalid ObjectId format",
    "content": {
        "application/json": {
            "schema": {
                **ERROR_RESPONSE_SCHEMA,
                "example": {
                    "success": False,
                    "message": "The provided ID 'invalid_id' is not a valid ObjectId",
                    "error": {
                        "message": "The provided ID 'invalid_id' is not a valid ObjectId",
                        "code": "INVALID_OBJECT_ID",
                        "details": None
                    },
                    "timestamp": "2024-01-01T12:00:00.000Z"
                }
            }
        }
    }
}

ERROR_400_VALIDATION = {
    "description": "Bad Request - Request validation failed",
    "content": {
        "application/json": {
            "schema": {
                **ERROR_RESPONSE_SCHEMA,
                "example": {
                    "success": False,
                    "message": "No valid fields provided for update.",
                    "error": {
                        "message": "No valid fields provided for update.",
                        "code": "NO_UPDATE_DATA",
                        "details": None
                    },
                    "timestamp": "2024-01-01T12:00:00.000Z"
                }
            }
        }
    }
}

# Combined 400 response for search endpoints (covers both invalid operator and missing params)
ERROR_400_SEARCH_ERRORS = {
    "description": "Bad Request - Invalid search operator or missing search parameters",
    "content": {
        "application/json": {
            "schema": ERROR_RESPONSE_SCHEMA,
            "examples": {
                "invalid_operator": {
                    "summary": "Invalid search operator",
                    "value": {
                        "success": False,
                        "message": "Invalid search operator 'invalid'. The search operator must be one of {'must', 'should', 'mustNot', 'filter'}.",
                        "error": {
                            "message": "Invalid search operator 'invalid'. The search operator must be one of {'must', 'should', 'mustNot', 'filter'}.",
                            "code": "INVALID_SEARCH_OPERATOR",
                            "details": None
                        },
                        "timestamp": "2024-01-01T12:00:00.000Z"
                    }
                },
                "missing_params": {
                    "summary": "Missing search parameters",
                    "value": {
                        "success": False,
                        "message": "At least one search parameter must be provided.",
                        "error": {
                            "message": "At least one search parameter must be provided.",
                            "code": "MISSING_SEARCH_PARAMS",
                            "details": None
                        },
                        "timestamp": "2024-01-01T12:00:00.000Z"
                    }
                }
            }
        }
    }
}

# 401 Unauthorized Responses
ERROR_401_VOYAGE_AUTH = {
    "description": "Unauthorized - Invalid Voyage AI API key",
    "content": {
        "application/json": {
            "schema": {
                **ERROR_RESPONSE_SCHEMA,
                "example": {
                    "success": False,
                    "message": "Invalid Voyage AI API key",
                    "error": {
                        "message": "Invalid Voyage AI API key",
                        "code": "VOYAGE_AUTH_ERROR",
                        "details": "Please verify your VOYAGE_API_KEY is correct in the .env file"
                    },
                    "timestamp": "2024-01-01T12:00:00.000Z"
                }
            }
        }
    }
}

# 404 Not Found Responses
ERROR_404_MOVIE_NOT_FOUND = {
    "description": "Not Found - Movie not found",
    "content": {
        "application/json": {
            "schema": {
                **ERROR_RESPONSE_SCHEMA,
                "example": {
                    "success": False,
                    "message": "No movie found with ID: 507f1f77bcf86cd799439011",
                    "error": {
                        "message": "No movie found with ID: 507f1f77bcf86cd799439011",
                        "code": "MOVIE_NOT_FOUND",
                        "details": None
                    },
                    "timestamp": "2024-01-01T12:00:00.000Z"
                }
            }
        }
    }
}

# 422 Unprocessable Entity - FastAPI's auto-generated validation errors
FASTAPI_422_VALIDATION_ERROR = {
    "description": "Unprocessable Entity - Validation error",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "loc": {"type": "array"},
                                "msg": {"type": "string"},
                                "type": {"type": "string"}
                            }
                        }
                    }
                },
                "example": {
                    "detail": [
                        {
                            "loc": ["body", "title"],
                            "msg": "field required",
                            "type": "value_error.missing"
                        }
                    ]
                }
            }
        }
    }
}

# 500 Internal Server Error Responses
ERROR_500_DATABASE = {
    "description": "Internal Server Error - Database operation failed",
    "content": {
        "application/json": {
            "schema": {
                **ERROR_RESPONSE_SCHEMA,
                "example": {
                    "success": False,
                    "message": "Database error occurred: Connection timeout",
                    "error": {
                        "message": "Database error occurred: Connection timeout",
                        "code": "DATABASE_ERROR",
                        "details": None
                    },
                    "timestamp": "2024-01-01T12:00:00.000Z"
                }
            }
        }
    }
}

ERROR_500_SEARCH = {
    "description": "Internal Server Error - Search operation failed",
    "content": {
        "application/json": {
            "schema": {
                **ERROR_RESPONSE_SCHEMA,
                "example": {
                    "success": False,
                    "message": "An error occurred while performing the search: Index not found",
                    "error": {
                        "message": "An error occurred while performing the search: Index not found",
                        "code": "SEARCH_ERROR",
                        "details": None
                    },
                    "timestamp": "2024-01-01T12:00:00.000Z"
                }
            }
        }
    }
}

ERROR_500_VECTOR_SEARCH = {
    "description": "Internal Server Error - Vector search operation failed",
    "content": {
        "application/json": {
            "schema": {
                **ERROR_RESPONSE_SCHEMA,
                "example": {
                    "success": False,
                    "message": "Error performing vector search: Embedding generation failed",
                    "error": {
                        "message": "Error performing vector search: Embedding generation failed",
                        "code": "VECTOR_SEARCH_ERROR",
                        "details": None
                    },
                    "timestamp": "2024-01-01T12:00:00.000Z"
                }
            }
        }
    }
}

# 503 Service Unavailable Responses
ERROR_503_VOYAGE = {
    "description": "Service Unavailable - Vector search service unavailable",
    "content": {
        "application/json": {
            "schema": ERROR_RESPONSE_SCHEMA,
            "examples": {
                "api_key_not_configured": {
                    "summary": "Voyage API key not configured",
                    "value": {
                        "success": False,
                        "message": "Vector search unavailable: VOYAGE_API_KEY not configured. Please add your API key to the .env file",
                        "error": {
                            "message": "Vector search unavailable: VOYAGE_API_KEY not configured. Please add your API key to the .env file",
                            "code": "SERVICE_UNAVAILABLE",
                            "details": None
                        },
                        "timestamp": "2024-01-01T12:00:00.000Z"
                    }
                },
                "voyage_api_error": {
                    "summary": "Voyage AI API error",
                    "value": {
                        "success": False,
                        "message": "Vector search service unavailable",
                        "error": {
                            "message": "Vector search service unavailable",
                            "code": "VOYAGE_API_ERROR",
                            "details": "Voyage AI service temporarily unavailable"
                        },
                        "timestamp": "2024-01-01T12:00:00.000Z"
                    }
                }
            }
        }
    }
}


# Common response combinations for different endpoint types
OBJECTID_VALIDATION_RESPONSES = {
    400: ERROR_400_INVALID_OBJECTID,
    404: ERROR_404_MOVIE_NOT_FOUND,
    500: ERROR_500_DATABASE
}

SEARCH_ENDPOINT_RESPONSES = {
    400: ERROR_400_SEARCH_ERRORS,
    500: ERROR_500_SEARCH
}

VECTOR_SEARCH_RESPONSES = {
    401: ERROR_401_VOYAGE_AUTH,
    500: ERROR_500_VECTOR_SEARCH,
    503: ERROR_503_VOYAGE
}

DATABASE_OPERATION_RESPONSES = {
    500: ERROR_500_DATABASE
}

CRUD_OPERATION_RESPONSES = {
    400: ERROR_400_VALIDATION,
    422: FASTAPI_422_VALIDATION_ERROR,
    500: ERROR_500_DATABASE
}

CRUD_WITH_OBJECTID_RESPONSES = {
    **OBJECTID_VALIDATION_RESPONSES,
    422: FASTAPI_422_VALIDATION_ERROR
}