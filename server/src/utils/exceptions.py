"""
Custom exception classes for the FastAPI application.

This module defines custom exceptions for handling specific error scenarios,
particularly for Voyage AI API interactions.
"""

class VoyageAuthError(Exception):
    """
    Exception raised when Voyage AI API authentication fails.
    
    This typically occurs when:
    - The API key is invalid
    - The API key is missing
    - The API key has expired
    """
    def __init__(self, message: str = "Invalid Voyage AI API key"):
        self.message = message
        super().__init__(self.message)


class VoyageAPIError(Exception):
    """
    Exception raised when Voyage AI API returns an error.
    
    This covers general API errors such as:
    - Rate limiting
    - Service unavailability
    - Invalid requests
    - Server errors
    """
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

