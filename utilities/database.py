import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING
from typing import Optional
import asyncio
from loguru import logger


class Database:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
            database_name = os.getenv("DATABASE_NAME", "book_crawler")
            
            self.client = AsyncIOMotorClient(mongodb_url)
            self.database = self.client[database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB database: {database_name}")
            
            # Create indexes
            await self.create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def create_indexes(self):
        """Create database indexes for efficient querying"""
        try:
            # Books collection indexes
            books_indexes = [
                IndexModel([("name", ASCENDING)]),
                IndexModel([("category", ASCENDING)]),
                IndexModel([("price_including_tax", ASCENDING)]),
                IndexModel([("rating", ASCENDING)]),
                IndexModel([("source_url", ASCENDING)], unique=True),
                IndexModel([("content_hash", ASCENDING)]),
                IndexModel([("crawl_timestamp", DESCENDING)])
            ]
            
            await self.database.books.create_indexes(books_indexes)
            
            # Book updates collection indexes
            updates_indexes = [
                IndexModel([("book_id", ASCENDING)]),
                IndexModel([("timestamp", DESCENDING)]),
                IndexModel([("field", ASCENDING)])
            ]
            
            await self.database.book_updates.create_indexes(updates_indexes)
            
            # Crawl status collection indexes
            crawl_indexes = [
                IndexModel([("start_time", DESCENDING)]),
                IndexModel([("status", ASCENDING)])
            ]
            
            await self.database.crawl_status.create_indexes(crawl_indexes)
            
            # API keys collection indexes
            api_key_indexes = [
                IndexModel([("key", ASCENDING)], unique=True),
                IndexModel([("name", ASCENDING)]),
                IndexModel([("is_active", ASCENDING)])
            ]
            
            await self.database.api_keys.create_indexes(api_key_indexes)
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise
    
    def get_books_collection(self):
        """Get books collection"""
        return self.database.books
    
    def get_updates_collection(self):
        """Get book updates collection"""
        return self.database.book_updates
    
    def get_crawl_status_collection(self):
        """Get crawl status collection"""
        return self.database.crawl_status
    
    def get_api_keys_collection(self):
        """Get API keys collection"""
        return self.database.api_keys


# Global database instance
db = Database()
