# Book Crawler - Web Crawling Solution for filersKeepers

A comprehensive web crawling solution for monitoring and serving data from https://books.toscrape.com. This project implements a scalable, fault-tolerant web crawler with change detection, RESTful APIs, and production-ready features.

## Features

### Part 1: Robust Web Crawler
- **Async crawling** with httpx for high performance
- **Retry logic** with exponential backoff for handling transient errors
- **MongoDB storage** with proper indexing and deduplication
- **Resume capability** from last successful crawl
- **Content hashing** for change detection
- **Raw HTML snapshots** as fallback
- **Pydantic models** for data validation

### Part 2: Scheduler and Change Detection
- **Daily scheduling** with APScheduler
- **Change detection** using content hash comparison
- **Email alerts** for new books and significant changes
- **Change logging** with detailed audit trail
- **Daily reports** in JSON format
- **Error handling** and recovery

### Part 3: RESTful API Server
- **FastAPI** with automatic OpenAPI documentation
- **API key authentication** with rate limiting
- **Advanced filtering** by category, price, rating
- **Pagination support** for large datasets
- **Change tracking** endpoints
- **Comprehensive error handling**

## Project Structure

```
webCrawler/
├── api/                    # FastAPI REST server
│   ├── __init__.py
│   ├── main.py            # FastAPI app and endpoints
│   ├── auth.py            # API key authentication
│   └── routes.py          # API routes and handlers
├── crawler/               # Web crawler implementation
│   ├── __init__.py
│   └── book_crawler.py    # Main crawler logic
├── scheduler/             # Change detection and scheduling
│   ├── __init__.py
│   └── change_detector.py # Scheduler and change detection
├── utilities/             # Shared utilities
│   ├── __init__.py
│   ├── models.py          # Pydantic models
│   ├── database.py        # MongoDB connection and indexes
│   └── config.py          # Configuration management
├── tests/                 # Test files
│   └── __init__.py
├── logs/                  # Log files
├── reports/               # Daily reports
├── main.py                # Main entry point
├── requirements.txt       # Python dependencies
├── env.example           # Environment configuration template
└── README.md             # This file
```

## Setup Instructions

### Prerequisites
- Python 3.8+
- MongoDB 4.4+
- Git

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd webCrawler
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Setup MongoDB:**
```bash
# Start MongoDB service
sudo systemctl start mongod  # Linux
# or
brew services start mongodb-community  # macOS
```

5. **Configure environment:**
```bash
cp env.example .env
# Edit .env with your configuration
```

### Environment Configuration

Key configuration variables in `.env`:

```env
# Database
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=book_crawler

# API
API_SECRET_KEY=your-secret-key-here
API_RATE_LIMIT=100
API_RATE_WINDOW=3600

# Crawler
CRAWLER_BASE_URL=https://books.toscrape.com
CRAWLER_MAX_RETRIES=3
CRAWLER_CONCURRENT_REQUESTS=10

# Email Alerts
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=admin@filerskeepers.co
```

## Usage

### Running Components

1. **Run the crawler:**
```bash
python main.py crawler
```

2. **Run the scheduler (change detection):**
```bash
python main.py scheduler
```

3. **Run the API server:**
```bash
python main.py api
```

4. **Run all components:**
```bash
python main.py all
```

### API Usage

1. **Start the API server:**
```bash
python main.py api
```

2. **Create an API key:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/create-key?name=my-key"
```

3. **Use the API:**
```bash
# Get all books
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "http://localhost:8000/api/v1/books"

# Get books with filters
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "http://localhost:8000/api/v1/books?category=Science&min_price=10&max_price=50&rating=Four"

# Get specific book
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "http://localhost:8000/api/v1/books/BOOK_ID"

# Get recent changes
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "http://localhost:8000/api/v1/changes?days=7"
```

### API Documentation

Once the API server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## MongoDB Schema

### Books Collection
```json
{
  "_id": "ObjectId",
  "name": "Book Title",
  "description": "Book description...",
  "category": "Fiction",
  "price_including_tax": 15.99,
  "price_excluding_tax": 15.99,
  "availability": "In stock (19 available)",
  "number_of_reviews": 5,
  "image_url": "http://books.toscrape.com/media/cache/...",
  "rating": "Four",
  "source_url": "http://books.toscrape.com/catalogue/...",
  "crawl_timestamp": "2024-01-15T10:30:00Z",
  "content_hash": "md5hash",
  "raw_html": "<html>...</html>"
}
```

### Book Updates Collection
```json
{
  "_id": "ObjectId",
  "book_id": "book_object_id",
  "field": "price_including_tax",
  "old_value": "15.99",
  "new_value": "17.99",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Testing

Run tests with pytest:
```bash
pytest tests/ -v
```

## Production Deployment

### Docker Deployment (Optional)

Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py", "api"]
```

### Environment Variables for Production
- Set `MONGODB_URL` to your production MongoDB instance
- Use a secure `API_SECRET_KEY`
- Configure proper email settings for alerts
- Set appropriate rate limits based on your needs

## Monitoring and Logging

- **Logs:** Check `logs/crawler.log` for detailed operation logs
- **Reports:** Daily reports saved in `reports/` directory
- **Health Check:** `GET /health` endpoint for service monitoring
- **Metrics:** API usage tracked in MongoDB

## Error Handling

The system includes comprehensive error handling:
- **Network errors:** Retry logic with exponential backoff
- **Database errors:** Connection pooling and reconnection
- **API errors:** Proper HTTP status codes and error messages
- **Scheduler errors:** Email alerts for critical failures

## Performance Features

- **Async/await:** Non-blocking I/O operations
- **Connection pooling:** Efficient HTTP connections
- **Database indexing:** Optimized queries
- **Rate limiting:** API protection
- **Concurrent crawling:** Configurable parallelism

## Security Features

- **API key authentication:** Secure access control
- **Rate limiting:** DoS protection
- **Input validation:** Pydantic model validation
- **SQL injection protection:** MongoDB driver safety
- **CORS configuration:** Cross-origin request handling

## Contact

For questions or issues, contact:
- **Technical:** sudipto@filerskeepers.co
- **General:** abdul@filerskeepers.co

---

**Note:** This is a production-ready solution with proper error handling, logging, testing, and documentation as requested for the filersKeepers Senior Python Developer position.
