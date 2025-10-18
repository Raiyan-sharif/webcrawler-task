#!/usr/bin/env python3
"""
Main entry point for the Book Crawler application.
Run different components based on command line arguments.
"""

import asyncio
import sys
import argparse
from loguru import logger
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.config import config
from utilities.database import db
from crawler.book_crawler import BookCrawler
from scheduler.change_detector import ChangeDetector
from api.main import app
import uvicorn


async def run_crawler():
    """Run the book crawler"""
    logger.info("Starting book crawler...")
    
    try:
        async with BookCrawler() as crawler:
            books = await crawler.crawl_books()
            logger.info(f"Successfully crawled {len(books)} books")
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        sys.exit(1)


async def run_scheduler():
    """Run the change detector scheduler"""
    logger.info("Starting change detector scheduler...")
    
    detector = ChangeDetector()
    
    try:
        await detector.start_scheduler()
        logger.info("Change detector started. Press Ctrl+C to stop.")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping change detector...")
    finally:
        await detector.stop_scheduler()


def run_api():
    """Run the FastAPI server"""
    logger.info("Starting API server...")
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=config.LOG_LEVEL.lower()
    )


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Book Crawler Application")
    parser.add_argument(
        "command",
        choices=["crawler", "scheduler", "api", "all"],
        help="Command to run: crawler, scheduler, api, or all"
    )
    parser.add_argument(
        "--max-books",
        type=int,
        help="Maximum number of books to crawl (for testing)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger.add(
        config.LOG_FILE,
        rotation="1 day",
        retention="7 days",
        level=config.LOG_LEVEL
    )
    
    # Connect to database
    await db.connect()
    
    try:
        if args.command == "crawler":
            await run_crawler()
        elif args.command == "scheduler":
            await run_scheduler()
        elif args.command == "api":
            await db.disconnect()  # API will manage its own connection
            run_api()
        elif args.command == "all":
            # Run crawler first, then start scheduler and API
            await run_crawler()
            
            # Start scheduler in background
            scheduler_task = asyncio.create_task(run_scheduler())
            
            # Start API in background
            api_task = asyncio.create_task(asyncio.to_thread(run_api))
            
            try:
                await asyncio.gather(scheduler_task, api_task)
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                scheduler_task.cancel()
                api_task.cancel()
                
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
