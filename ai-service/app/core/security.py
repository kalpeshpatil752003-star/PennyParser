from fastapi import Header, HTTPException, status
from app.core.config import INTERNAL_SERVICE_TOKEN

def verify_internal_token(x_internal_token: str = Header(None)):
    if not x_internal_token or x_internal_token != INTERNAL_SERVICE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing internal service token"
        )
