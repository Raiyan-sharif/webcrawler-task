from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager

from utilities.config import config
from utilities.database import db
from utilities.models import Book, BookUpdate, APIKey
from api.auth import get_current_api_key, create_api_key
from api.routes import books_router, changes_router


security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await db.connect()
    # Optionally auto-create a default API key for local/dev and write it to a file
    if config.AUTO_CREATE_API_KEY:
        try:
            api_key = await create_api_key(config.DEFAULT_API_KEY_NAME)
            import os
            os.makedirs(os.path.dirname(config.DEFAULT_API_KEY_OUTPUT), exist_ok=True)
            with open(config.DEFAULT_API_KEY_OUTPUT, 'w') as f:
                f.write(api_key.key)
        except Exception:
            # Swallow errors so startup continues
            pass
    yield
    # Shutdown
    await db.disconnect()


app = FastAPI(
    title="Book Crawler API",
    description="RESTful API for book crawling and monitoring system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(books_router, prefix="/api/v1", tags=["books"])
app.include_router(changes_router, prefix="/api/v1", tags=["changes"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Book Crawler API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        await db.client.admin.command('ping')
        return {"status": "healthy", "timestamp": datetime.utcnow()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


@app.post("/api/v1/auth/create-key")
async def create_api_key_endpoint(name: str = Query(..., description="Name for the API key")):
    """Create a new API key"""
    api_key = await create_api_key(name)
    return {"api_key": api_key.key, "name": api_key.name, "created_at": api_key.created_at}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
