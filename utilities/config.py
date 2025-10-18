import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for the application"""
    
    # Database Configuration
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "book_crawler")
    
    # API Configuration
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "your-secret-key-here")
    API_RATE_LIMIT: int = int(os.getenv("API_RATE_LIMIT", "100"))
    API_RATE_WINDOW: int = int(os.getenv("API_RATE_WINDOW", "3600"))
    
    # Crawler Configuration
    CRAWLER_BASE_URL: str = os.getenv("CRAWLER_BASE_URL", "https://books.toscrape.com")
    CRAWLER_MAX_RETRIES: int = int(os.getenv("CRAWLER_MAX_RETRIES", "3"))
    CRAWLER_RETRY_DELAY: float = float(os.getenv("CRAWLER_RETRY_DELAY", "1.0"))
    CRAWLER_CONCURRENT_REQUESTS: int = int(os.getenv("CRAWLER_CONCURRENT_REQUESTS", "10"))
    CRAWLER_REQUEST_DELAY: float = float(os.getenv("CRAWLER_REQUEST_DELAY", "0.5"))
    
    # Scheduler Configuration
    SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE", "UTC")
    SCHEDULER_DAILY_TIME: str = os.getenv("SCHEDULER_DAILY_TIME", "02:00")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/crawler.log")
    
    # Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    ALERT_EMAIL: str = os.getenv("ALERT_EMAIL", "admin@filerskeepers.co")


config = Config()
