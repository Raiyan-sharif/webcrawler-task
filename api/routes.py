from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId

from utilities.database import db
from utilities.models import Book, BookUpdate
from api.auth import get_current_api_key, APIKey

books_router = APIRouter()
changes_router = APIRouter()


@books_router.get("/books")
async def get_books(
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    rating: Optional[str] = Query(None, description="Filter by rating (One, Two, Three, Four, Five)"),
    sort_by: Optional[str] = Query("name", description="Sort by field (name, price_including_tax, rating, number_of_reviews)"),
    sort_order: Optional[str] = Query("asc", description="Sort order (asc, desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Get books with filtering, sorting, and pagination"""
    
    # Build query filter
    query_filter = {}
    
    if category:
        query_filter["category"] = {"$regex": category, "$options": "i"}
    
    if min_price is not None or max_price is not None:
        price_filter = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        query_filter["price_including_tax"] = price_filter
    
    if rating:
        query_filter["rating"] = rating
    
    # Build sort
    sort_field = sort_by if sort_by in ["name", "price_including_tax", "rating", "number_of_reviews"] else "name"
    sort_direction = 1 if sort_order == "asc" else -1
    sort_criteria = [(sort_field, sort_direction)]
    
    # Calculate pagination
    skip = (page - 1) * page_size
    
    try:
        # Get total count
        total_count = await db.get_books_collection().count_documents(query_filter)
        
        # Get books
        cursor = db.get_books_collection().find(query_filter).sort(sort_criteria).skip(skip).limit(page_size)
        books = await cursor.to_list(length=page_size)
        
        # Convert ObjectId to string for JSON serialization
        for book in books:
            book["id"] = str(book["_id"])
            del book["_id"]
        
        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "books": books,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching books: {str(e)}"
        )


@books_router.get("/books/{book_id}")
async def get_book(
    book_id: str,
    api_key: APIKey = Depends(get_current_api_key)
):
    """Get a specific book by ID"""
    
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(book_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid book ID format"
            )
        
        book = await db.get_books_collection().find_one({"_id": ObjectId(book_id)})
        
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )
        
        # Convert ObjectId to string
        book["id"] = str(book["_id"])
        del book["_id"]
        
        return book
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching book: {str(e)}"
        )


@changes_router.get("/changes")
async def get_changes(
    book_id: Optional[str] = Query(None, description="Filter changes by book ID"),
    field: Optional[str] = Query(None, description="Filter changes by field name"),
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Get recent changes with filtering and pagination"""
    
    # Build query filter
    query_filter = {}
    
    if book_id:
        if not ObjectId.is_valid(book_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid book ID format"
            )
        query_filter["book_id"] = book_id
    
    if field:
        query_filter["field"] = field
    
    # Add date filter
    from_date = datetime.utcnow() - timedelta(days=days)
    query_filter["timestamp"] = {"$gte": from_date}
    
    # Calculate pagination
    skip = (page - 1) * page_size
    
    try:
        # Get total count
        total_count = await db.get_updates_collection().count_documents(query_filter)
        
        # Get changes
        cursor = db.get_updates_collection().find(query_filter).sort([("timestamp", -1)]).skip(skip).limit(page_size)
        changes = await cursor.to_list(length=page_size)
        
        # Convert ObjectId to string for JSON serialization
        for change in changes:
            if "_id" in change:
                change["id"] = str(change["_id"])
                del change["_id"]
        
        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "changes": changes,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching changes: {str(e)}"
        )


@changes_router.get("/changes/summary")
async def get_changes_summary(
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Get summary of recent changes"""
    
    from_date = datetime.utcnow() - timedelta(days=days)
    
    try:
        # Get change counts by type
        pipeline = [
            {"$match": {"timestamp": {"$gte": from_date}}},
            {"$group": {
                "_id": "$field",
                "count": {"$sum": 1},
                "latest_change": {"$max": "$timestamp"}
            }},
            {"$sort": {"count": -1}}
        ]
        
        changes_by_field = await db.get_updates_collection().aggregate(pipeline).to_list(length=None)
        
        # Get total changes count
        total_changes = await db.get_updates_collection().count_documents({"timestamp": {"$gte": from_date}})
        
        # Get unique books changed
        unique_books = await db.get_updates_collection().distinct("book_id", {"timestamp": {"$gte": from_date}})
        
        return {
            "summary": {
                "total_changes": total_changes,
                "unique_books_changed": len(unique_books),
                "period_days": days
            },
            "changes_by_field": changes_by_field
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching changes summary: {str(e)}"
        )
