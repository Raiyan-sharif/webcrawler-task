from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class BookRating(str, Enum):
    ONE = "One"
    TWO = "Two"
    THREE = "Three"
    FOUR = "Four"
    FIVE = "Five"


class Book(BaseModel):
    """Book model for storing book information"""
    id: Optional[str] = None
    name: str = Field(..., description="Name of the book")
    description: str = Field(..., description="Description of the book")
    category: str = Field(..., description="Book category")
    price_including_tax: float = Field(..., description="Price including tax")
    price_excluding_tax: float = Field(..., description="Price excluding tax")
    availability: str = Field(..., description="Availability status")
    number_of_reviews: int = Field(..., description="Number of reviews")
    image_url: str = Field(..., description="URL of the book cover image")
    rating: BookRating = Field(..., description="Book rating")
    source_url: str = Field(..., description="Source URL of the book")
    crawl_timestamp: datetime = Field(default_factory=datetime.utcnow)
    content_hash: str = Field(..., description="Hash of the book content for change detection")
    raw_html: Optional[str] = Field(None, description="Raw HTML snapshot")
    
    @validator('price_including_tax', 'price_excluding_tax')
    def validate_prices(cls, v):
        if v < 0:
            raise ValueError('Price cannot be negative')
        return v
    
    @validator('number_of_reviews')
    def validate_reviews(cls, v):
        if v < 0:
            raise ValueError('Number of reviews cannot be negative')
        return v


class BookUpdate(BaseModel):
    """Model for book updates"""
    book_id: str
    field: str
    old_value: str
    new_value: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CrawlStatus(BaseModel):
    """Model for tracking crawl status"""
    id: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str  # "running", "completed", "failed"
    total_pages: int = 0
    pages_crawled: int = 0
    books_found: int = 0
    errors: List[str] = []
    last_crawled_page: Optional[str] = None


class APIKey(BaseModel):
    """Model for API authentication"""
    key: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    rate_limit: int = 100
    requests_made: int = 0
    last_reset: datetime = Field(default_factory=datetime.utcnow)
