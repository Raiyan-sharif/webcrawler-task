import pytest
from datetime import datetime
from utilities.models import Book, BookRating, BookUpdate, APIKey


class TestBookModel:
    """Test Book model validation"""
    
    def test_valid_book(self):
        """Test creating a valid book"""
        book_data = {
            "name": "Test Book",
            "description": "A test book description",
            "category": "Fiction",
            "price_including_tax": 15.99,
            "price_excluding_tax": 15.99,
            "availability": "In stock",
            "number_of_reviews": 5,
            "image_url": "http://example.com/image.jpg",
            "rating": BookRating.FOUR,
            "source_url": "http://example.com/book",
            "content_hash": "testhash123"
        }
        
        book = Book(**book_data)
        assert book.name == "Test Book"
        assert book.price_including_tax == 15.99
        assert book.rating == BookRating.FOUR
    
    def test_invalid_price(self):
        """Test book with invalid price"""
        book_data = {
            "name": "Test Book",
            "description": "A test book description",
            "category": "Fiction",
            "price_including_tax": -5.0,  # Invalid negative price
            "price_excluding_tax": 15.99,
            "availability": "In stock",
            "number_of_reviews": 5,
            "image_url": "http://example.com/image.jpg",
            "rating": BookRating.FOUR,
            "source_url": "http://example.com/book",
            "content_hash": "testhash123"
        }
        
        with pytest.raises(ValueError, match="Price cannot be negative"):
            Book(**book_data)
    
    def test_invalid_reviews(self):
        """Test book with invalid number of reviews"""
        book_data = {
            "name": "Test Book",
            "description": "A test book description",
            "category": "Fiction",
            "price_including_tax": 15.99,
            "price_excluding_tax": 15.99,
            "availability": "In stock",
            "number_of_reviews": -1,  # Invalid negative reviews
            "image_url": "http://example.com/image.jpg",
            "rating": BookRating.FOUR,
            "source_url": "http://example.com/book",
            "content_hash": "testhash123"
        }
        
        with pytest.raises(ValueError, match="Number of reviews cannot be negative"):
            Book(**book_data)


class TestBookUpdateModel:
    """Test BookUpdate model"""
    
    def test_valid_book_update(self):
        """Test creating a valid book update"""
        update = BookUpdate(
            book_id="test_id",
            field="price_including_tax",
            old_value="15.99",
            new_value="17.99"
        )
        
        assert update.book_id == "test_id"
        assert update.field == "price_including_tax"
        assert update.old_value == "15.99"
        assert update.new_value == "17.99"
        assert isinstance(update.timestamp, datetime)


class TestAPIKeyModel:
    """Test APIKey model"""
    
    def test_valid_api_key(self):
        """Test creating a valid API key"""
        api_key = APIKey(
            key="test_key_hash",
            name="test_key"
        )
        
        assert api_key.key == "test_key_hash"
        assert api_key.name == "test_key"
        assert api_key.is_active is True
        assert api_key.rate_limit == 100
        assert api_key.requests_made == 0
        assert isinstance(api_key.created_at, datetime)
