"""
Utility functions for creating standardized error responses.

This module provides functions to create consistent error response structures
that match the Express backend's error format.
"""

from datetime import datetime, timezone
from typing import Optional, Any


def create_error_response(
    message: str,
    code: Optional[str] = None,
    details: Optional[Any] = None
) -> dict:
    """
    Creates a standardized error response.
    
    Args:
        message: The error message to display
        code: Optional error code (e.g., 'VOYAGE_AUTH_ERROR', 'VOYAGE_API_ERROR')
        details: Optional additional error details
        
    Returns:
        A dictionary containing the standardized error response
    """
    return {
        "success": False,
        "message": message,
        "error": {
            "message": message,
            "code": code,
            "details": details
        },
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }

