import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from utilities.config import config
from utilities.database import db
from utilities.models import APIKey

security = HTTPBearer()


async def create_api_key(name: str) -> APIKey:
    """Create a new API key"""
    # Generate a secure random key
    key = secrets.token_urlsafe(32)
    
    # Hash the key for storage
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    
    api_key = APIKey(
        key=key_hash,
        name=name,
        rate_limit=config.API_RATE_LIMIT,
        requests_made=0,
        last_reset=datetime.utcnow()
    )
    
    # Store in database
    await db.get_api_keys_collection().insert_one(api_key.dict())
    
    # Return the original key (not the hash)
    api_key.key = key
    return api_key


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> APIKey:
    """Verify API key and return API key object"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # Hash the provided key
    provided_key_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    
    # Find the API key in database
    api_key_doc = await db.get_api_keys_collection().find_one({
        "key": provided_key_hash,
        "is_active": True
    })
    
    if not api_key_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    api_key = APIKey(**api_key_doc)
    
    # Check rate limit
    now = datetime.utcnow()
    if now - api_key.last_reset > timedelta(seconds=config.API_RATE_WINDOW):
        # Reset rate limit
        api_key.requests_made = 0
        api_key.last_reset = now
        await db.get_api_keys_collection().update_one(
            {"_id": api_key_doc["_id"]},
            {"$set": {"requests_made": 0, "last_reset": now}}
        )
    
    if api_key.requests_made >= api_key.rate_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Increment request count
    await db.get_api_keys_collection().update_one(
        {"_id": api_key_doc["_id"]},
        {"$inc": {"requests_made": 1}}
    )
    
    return api_key


async def get_current_api_key(api_key: APIKey = Depends(verify_api_key)) -> APIKey:
    """Get current API key (dependency)"""
    return api_key
