import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from crawler.book_crawler import BookCrawler
from utilities.models import Book, BookRating


class TestBookCrawler:
    """Test BookCrawler functionality"""
    
    @pytest.mark.asyncio
    async def test_parse_rating(self):
        """Test rating parsing"""
        crawler = BookCrawler()
        
        assert crawler.parse_rating("One") == BookRating.ONE
        assert crawler.parse_rating("Two") == BookRating.TWO
        assert crawler.parse_rating("Three") == BookRating.THREE
        assert crawler.parse_rating("Four") == BookRating.FOUR
        assert crawler.parse_rating("Five") == BookRating.FIVE
        assert crawler.parse_rating("Invalid") == BookRating.ONE  # Default
    
    @pytest.mark.asyncio
    async def test_extract_price(self):
        """Test price extraction"""
        crawler = BookCrawler()
        
        assert crawler.extract_price("£15.99") == 15.99
        assert crawler.extract_price("£0.00") == 0.0
        assert crawler.extract_price("Invalid") == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_content_hash(self):
        """Test content hash calculation"""
        crawler = BookCrawler()
        
        book_data = {
            'name': 'Test Book',
            'price_including_tax': 15.99,
            'availability': 'In stock'
        }
        
        hash1 = crawler.calculate_content_hash(book_data)
        hash2 = crawler.calculate_content_hash(book_data)
        
        assert hash1 == hash2  # Same data should produce same hash
        
        # Different data should produce different hash
        book_data['price_including_tax'] = 17.99
        hash3 = crawler.calculate_content_hash(book_data)
        assert hash1 != hash3
    
    @pytest.mark.asyncio
    async def test_fetch_page_retry_logic(self):
        """Test fetch page retry logic"""
        crawler = BookCrawler()
        
        # Mock session that fails first two times, then succeeds
        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            AsyncMock(status_code=200, text="<html>Success</html>")
        ]
        
        crawler.session = mock_session
        
        result = await crawler.fetch_page("http://example.com", max_retries=2)
        assert result == "<html>Success</html>"
        assert mock_session.get.call_count == 3  # Called 3 times (2 failures + 1 success)
    
    @pytest.mark.asyncio
    async def test_fetch_page_max_retries_exceeded(self):
        """Test fetch page when max retries exceeded"""
        crawler = BookCrawler()
        
        # Mock session that always fails
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Network error")
        
        crawler.session = mock_session
        
        result = await crawler.fetch_page("http://example.com", max_retries=2)
        assert result is None
        assert mock_session.get.call_count == 3  # Called 3 times (initial + 2 retries)


@pytest.mark.asyncio
async def test_crawler_context_manager():
    """Test crawler as async context manager"""
    async with BookCrawler() as crawler:
        assert crawler.session is not None
        assert isinstance(crawler.session, AsyncMock.__class__.__bases__[0])
    
    # Session should be closed after context
    assert crawler.session is None
