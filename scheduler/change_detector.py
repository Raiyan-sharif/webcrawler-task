import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from utilities.config import config
from utilities.database import db
from utilities.models import BookUpdate, Book
from crawler.book_crawler import BookCrawler


class ChangeDetector:
    """Detects changes in book data and sends alerts"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=config.SCHEDULER_TIMEZONE)
        self.crawler = None
        
    async def start_scheduler(self):
        """Start the scheduler"""
        # Schedule daily crawl at configured time
        hour, minute = config.SCHEDULER_DAILY_TIME.split(':')
        self.scheduler.add_job(
            self.daily_crawl_and_detect_changes,
            CronTrigger(hour=int(hour), minute=int(minute)),
            id='daily_crawl',
            name='Daily Crawl and Change Detection',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Scheduler started - Daily crawl scheduled")
    
    async def stop_scheduler(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    async def daily_crawl_and_detect_changes(self):
        """Daily task to crawl and detect changes"""
        logger.info("Starting daily crawl and change detection")
        
        try:
            async with BookCrawler() as crawler:
                # Get current books from database
                existing_books = await self.get_existing_books()
                existing_urls = {book['source_url']: book for book in existing_books}
                
                # Get all book URLs from site
                book_urls = await crawler.get_all_book_urls()
                
                changes = []
                new_books = []
                updated_books = []
                
                # Process each book URL
                for url in book_urls:
                    try:
                        # Parse the book
                        current_book = await crawler.parse_book_page(url)
                        if not current_book:
                            continue
                        
                        # Check if it's a new book
                        if url not in existing_urls:
                            new_books.append(current_book)
                            changes.append({
                                'type': 'new_book',
                                'book_id': str(current_book.id),
                                'book_name': current_book.name,
                                'timestamp': datetime.utcnow()
                            })
                        else:
                            # Check for changes
                            existing_book = existing_urls[url]
                            book_changes = self.detect_book_changes(existing_book, current_book.dict())
                            
                            if book_changes:
                                updated_books.append(current_book)
                                changes.extend(book_changes)
                        
                    except Exception as e:
                        logger.error(f"Error processing book {url}: {e}")
                
                # Save changes to database
                if changes:
                    await self.save_changes(changes)
                
                # Send alerts if significant changes
                if new_books or updated_books:
                    await self.send_change_alert(new_books, updated_books, changes)
                
                # Generate daily report
                await self.generate_daily_report(new_books, updated_books, changes)
                
                logger.info(f"Daily crawl completed: {len(new_books)} new books, {len(updated_books)} updated books")
                
        except Exception as e:
            logger.error(f"Daily crawl failed: {e}")
            await self.send_error_alert(str(e))
    
    async def get_existing_books(self) -> List[Dict[str, Any]]:
        """Get all existing books from database"""
        books_collection = db.get_books_collection()
        books = await books_collection.find({}).to_list(length=None)
        return books
    
    def detect_book_changes(self, existing_book: Dict[str, Any], current_book: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect changes between existing and current book data"""
        changes = []
        
        # Fields to check for changes
        fields_to_check = [
            'name', 'description', 'category', 'price_including_tax',
            'price_excluding_tax', 'availability', 'number_of_reviews',
            'image_url', 'rating'
        ]
        
        for field in fields_to_check:
            existing_value = existing_book.get(field)
            current_value = current_book.get(field)
            
            if existing_value != current_value:
                change = {
                    'type': 'book_updated',
                    'book_id': str(existing_book.get('_id')),
                    'book_name': existing_book.get('name'),
                    'field': field,
                    'old_value': str(existing_value),
                    'new_value': str(current_value),
                    'timestamp': datetime.utcnow()
                }
                changes.append(change)
        
        return changes
    
    async def save_changes(self, changes: List[Dict[str, Any]]):
        """Save changes to database"""
        updates_collection = db.get_updates_collection()
        
        for change in changes:
            book_update = BookUpdate(
                book_id=change.get('book_id', ''),
                field=change.get('field', ''),
                old_value=change.get('old_value', ''),
                new_value=change.get('new_value', ''),
                timestamp=change.get('timestamp', datetime.utcnow())
            )
            await updates_collection.insert_one(book_update.dict())
        
        logger.info(f"Saved {len(changes)} changes to database")
    
    async def send_change_alert(self, new_books: List[Book], updated_books: List[Book], changes: List[Dict[str, Any]]):
        """Send email alert about changes"""
        if not config.SMTP_USERNAME or not config.SMTP_PASSWORD:
            logger.warning("Email configuration not set, skipping email alert")
            return
        
        try:
            # Create email content
            subject = f"Book Crawler Alert - {len(new_books)} new books, {len(updated_books)} updated"
            
            body = f"""
Book Crawler Daily Report - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

New Books ({len(new_books)}):
"""
            
            for book in new_books[:10]:  # Show first 10 new books
                body += f"- {book.name} (${book.price_including_tax})\n"
            
            if len(new_books) > 10:
                body += f"... and {len(new_books) - 10} more\n"
            
            body += f"\nUpdated Books ({len(updated_books)}):\n"
            
            # Group changes by book
            changes_by_book = {}
            for change in changes:
                if change['type'] == 'book_updated':
                    book_name = change['book_name']
                    if book_name not in changes_by_book:
                        changes_by_book[book_name] = []
                    changes_by_book[book_name].append(change)
            
            for book_name, book_changes in list(changes_by_book.items())[:10]:
                body += f"- {book_name}:\n"
                for change in book_changes:
                    body += f"  • {change['field']}: {change['old_value']} → {change['new_value']}\n"
            
            if len(changes_by_book) > 10:
                body += f"... and {len(changes_by_book) - 10} more books updated\n"
            
            # Send email
            await self.send_email(config.ALERT_EMAIL, subject, body)
            logger.info("Change alert email sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send change alert: {e}")
    
    async def send_error_alert(self, error_message: str):
        """Send error alert email"""
        if not config.SMTP_USERNAME or not config.SMTP_PASSWORD:
            return
        
        subject = "Book Crawler Error Alert"
        body = f"""
Book Crawler Error Report - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

Error: {error_message}

Please check the logs for more details.
"""
        
        try:
            await self.send_email(config.ALERT_EMAIL, subject, body)
            logger.info("Error alert email sent")
        except Exception as e:
            logger.error(f"Failed to send error alert: {e}")
    
    async def send_email(self, to_email: str, subject: str, body: str):
        """Send email"""
        msg = MIMEMultipart()
        msg['From'] = config.SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT)
        server.starttls()
        server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(config.SMTP_USERNAME, to_email, text)
        server.quit()
    
    async def generate_daily_report(self, new_books: List[Book], updated_books: List[Book], changes: List[Dict[str, Any]]):
        """Generate daily report in JSON format"""
        report = {
            'date': datetime.utcnow().isoformat(),
            'summary': {
                'new_books': len(new_books),
                'updated_books': len(updated_books),
                'total_changes': len(changes)
            },
            'new_books': [
                {
                    'name': book.name,
                    'category': book.category,
                    'price': book.price_including_tax,
                    'url': book.source_url
                } for book in new_books
            ],
            'changes': changes
        }
        
        # Save report to file
        import json
        report_filename = f"reports/daily_report_{datetime.utcnow().strftime('%Y%m%d')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Daily report saved to {report_filename}")


async def main():
    """Main function to run the scheduler"""
    from utilities.database import db
    await db.connect()
    
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
        await db.disconnect()


if __name__ == "__main__":
    # Create reports directory
    import os
    os.makedirs("reports", exist_ok=True)
    
    asyncio.run(main())
