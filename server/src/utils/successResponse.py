from datetime import datetime, timezone
from typing import Optional
from src.models.models import  SuccessResponse, T

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

