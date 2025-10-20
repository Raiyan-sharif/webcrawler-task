import asyncio
import httpx
import hashlib
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from loguru import logger
import time
from datetime import datetime

from utilities.config import config
from utilities.models import Book, BookRating, CrawlStatus
from utilities.database import db


class BookCrawler:
    """Async web crawler for books.toscrape.com"""
    
    def __init__(self):
        self.base_url = config.CRAWLER_BASE_URL
        self.session: Optional[httpx.AsyncClient] = None
        self.crawl_status_id: Optional[str] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=config.CRAWLER_CONCURRENT_REQUESTS)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.aclose()
    
    async def start_crawl(self) -> str:
        """Start a new crawl session and return crawl status ID"""
        crawl_status = CrawlStatus(
            start_time=datetime.utcnow(),
            status="running"
        )
        
        result = await db.get_crawl_status_collection().insert_one(crawl_status.dict())
        self.crawl_status_id = str(result.inserted_id)
        logger.info(f"Started crawl session: {self.crawl_status_id}")
        return self.crawl_status_id
    
    async def complete_crawl(self, books_found: int, errors: List[str]):
        """Complete the crawl session"""
        if self.crawl_status_id:
            await db.get_crawl_status_collection().update_one(
                {"_id": self.crawl_status_id},
                {
                    "$set": {
                        "end_time": datetime.utcnow(),
                        "status": "completed",
                        "books_found": books_found,
                        "errors": errors
                    }
                }
            )
            logger.info(f"Completed crawl session: {self.crawl_status_id}")
    
    async def fetch_page(self, url: str, max_retries: int = None) -> Optional[str]:
        """Fetch a page with retry logic"""
        if max_retries is None:
            max_retries = config.CRAWLER_MAX_RETRIES
            
        for attempt in range(max_retries + 1):
            try:
                response = await self.session.get(url)
                response.raise_for_status()
                return response.text
                
            except httpx.RequestError as e:
                logger.warning(f"Request error for {url} (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(config.CRAWLER_RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"Failed to fetch {url} after {max_retries + 1} attempts")
                    
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                break
                
        return None
    
    def parse_rating(self, rating_text: str) -> BookRating:
        """Parse rating text to BookRating enum"""
        rating_map = {
            "One": BookRating.ONE,
            "Two": BookRating.TWO,
            "Three": BookRating.THREE,
            "Four": BookRating.FOUR,
            "Five": BookRating.FIVE
        }
        return rating_map.get(rating_text, BookRating.ONE)
    
    def extract_price(self, price_text: str) -> float:
        """Extract price from text"""
        try:
            return float(price_text.replace("£", ""))
        except ValueError:
            return 0.0
    
    def calculate_content_hash(self, book_data: Dict[str, Any]) -> str:
        """Calculate hash for change detection"""
        # Create a string from key book data for hashing
        content_string = f"{book_data['name']}{book_data['price_including_tax']}{book_data['availability']}"
        return hashlib.md5(content_string.encode()).hexdigest()
    
    async def parse_book_page(self, book_url: str) -> Optional[Book]:
        """Parse individual book page"""
        try:
            html = await self.fetch_page(book_url)
            if not html:
                return None
                
            soup = BeautifulSoup(html, 'lxml')
            
            # Extract book information
            name = soup.select_one('h1').text.strip() if soup.select_one('h1') else ""
            
            # Description
            description_element = soup.select_one('#product_description + p')
            description = description_element.text.strip() if description_element else ""
            
            # Category
            breadcrumb = soup.select_one('.breadcrumb')
            category = ""
            if breadcrumb:
                category_link = breadcrumb.select('a')[-1]
                category = category_link.text.strip() if category_link else ""
            
            # Product information table parsing (more robust)
            price_including_tax = 0.0
            price_excluding_tax = 0.0
            availability = "Unknown"
            number_of_reviews = 0

            product_table = soup.select_one('table.table.table-striped')
            if product_table:
                for row in product_table.select('tr'):
                    header_el = row.select_one('th')
                    value_el = row.select_one('td')
                    if not header_el or not value_el:
                        continue
                    header = header_el.text.strip()
                    value = value_el.text.strip()
                    if header == 'Price (incl. tax)':
                        price_including_tax = self.extract_price(value)
                    elif header == 'Price (excl. tax)':
                        price_excluding_tax = self.extract_price(value)
                    elif header == 'Availability':
                        availability = value
                    elif header == 'Number of reviews':
                        try:
                            number_of_reviews = int(value)
                        except ValueError:
                            number_of_reviews = 0

            # Fallbacks if table not found
            if price_including_tax == 0.0:
                price_including_tax_text = soup.select_one('.price_color').text if soup.select_one('.price_color') else "£0.00"
                price_including_tax = self.extract_price(price_including_tax_text)
            if price_excluding_tax == 0.0:
                price_excluding_tax = price_including_tax
            if availability == "Unknown":
                availability_element = soup.select_one('.availability')
                availability = availability_element.text.strip() if availability_element else "Unknown"
            
            # Image URL
            image_element = soup.select_one('#product_gallery img')
            image_url = ""
            if image_element:
                image_url = urljoin(book_url, image_element.get('src', ''))
            
            # Rating
            rating_element = soup.select_one('.star-rating')
            rating = BookRating.ONE
            if rating_element:
                rating_class = rating_element.get('class', [])
                for cls in rating_class:
                    if cls.startswith('Five'):
                        rating = BookRating.FIVE
                        break
                    elif cls.startswith('Four'):
                        rating = BookRating.FOUR
                        break
                    elif cls.startswith('Three'):
                        rating = BookRating.THREE
                        break
                    elif cls.startswith('Two'):
                        rating = BookRating.TWO
                        break
            
            # Create book data
            book_data = {
                'name': name,
                'description': description,
                'category': category,
                'price_including_tax': price_including_tax,
                'price_excluding_tax': price_excluding_tax,
                'availability': availability,
                'number_of_reviews': number_of_reviews,
                'image_url': image_url,
                'rating': rating,
                'source_url': book_url,
                'raw_html': html
            }
            
            # Calculate content hash
            content_hash = self.calculate_content_hash(book_data)
            book_data['content_hash'] = content_hash
            
            book = Book(**book_data)
            return book
            
        except Exception as e:
            logger.error(f"Error parsing book page {book_url}: {e}")
            return None
    
    async def get_all_book_urls(self) -> List[str]:
        """Get all book URLs from all pages"""
        book_urls = []
        page_num = 1
        
        while True:
            page_url = f"{self.base_url}/catalogue/page-{page_num}.html"
            logger.info(f"Fetching page {page_num}: {page_url}")
            
            html = await self.fetch_page(page_url)
            if not html:
                logger.info(f"No more pages found at page {page_num}")
                break
                
            soup = BeautifulSoup(html, 'lxml')
            book_links = soup.select('h3 a')
            
            if not book_links:
                logger.info(f"No books found on page {page_num}")
                break
                
            for link in book_links:
                # Build absolute URL based on the listing page URL to handle relative paths like '../../../'
                book_url = urljoin(page_url, link.get('href', ''))
                book_urls.append(book_url)
            
            logger.info(f"Found {len(book_links)} books on page {page_num}")
            page_num += 1
            
            # Add delay between pages
            await asyncio.sleep(config.CRAWLER_REQUEST_DELAY)
        
        logger.info(f"Total book URLs found: {len(book_urls)}")
        return book_urls
    
    async def crawl_books(self, max_books: Optional[int] = None) -> List[Book]:
        """Crawl all books"""
        crawl_id = await self.start_crawl()
        
        try:
            # Get all book URLs
            book_urls = await self.get_all_book_urls()
            
            if max_books:
                book_urls = book_urls[:max_books]
            
            books = []
            errors = []
            
            # Create semaphore for concurrent requests
            semaphore = asyncio.Semaphore(config.CRAWLER_CONCURRENT_REQUESTS)
            
            async def crawl_single_book(url: str) -> Optional[Book]:
                async with semaphore:
                    try:
                        await asyncio.sleep(config.CRAWLER_REQUEST_DELAY)
                        book = await self.parse_book_page(url)
                        if book:
                            # Save to database
                            await db.get_books_collection().replace_one(
                                {"source_url": url},
                                book.dict(),
                                upsert=True
                            )
                        return book
                    except Exception as e:
                        error_msg = f"Error crawling {url}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        return None
            
            # Crawl books concurrently
            tasks = [crawl_single_book(url) for url in book_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            books = [book for book in results if book is not None and not isinstance(book, Exception)]
            
            # Update crawl status
            await db.get_crawl_status_collection().update_one(
                {"_id": crawl_id},
                {
                    "$set": {
                        "total_pages": len(book_urls),
                        "pages_crawled": len(books),
                        "books_found": len(books),
                        "errors": errors
                    }
                }
            )
            
            await self.complete_crawl(len(books), errors)
            logger.info(f"Crawling completed. Found {len(books)} books with {len(errors)} errors")
            
            return books
            
        except Exception as e:
            logger.error(f"Crawling failed: {e}")
            errors.append(str(e))
            await self.complete_crawl(0, errors)
            raise


async def main():
    """Main function to run the crawler"""
    await db.connect()
    
    try:
        async with BookCrawler() as crawler:
            books = await crawler.crawl_books()
            print(f"Successfully crawled {len(books)} books")
            
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
