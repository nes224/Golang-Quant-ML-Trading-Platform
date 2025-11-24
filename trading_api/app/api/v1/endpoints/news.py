from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.models.schemas import NewsCreate, NewsUpdate
from app.services.news import NewsManager

router = APIRouter()
news_manager = NewsManager()

@router.post("/news")
def create_news(news: NewsCreate):
    """Create a new news entry"""
    try:
        return news_manager.create_news(news.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/news/search")
def search_news(
    keyword: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sentiment: Optional[str] = None,
    source: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    limit: int = Query(default=100, le=500)
):
    """Search news with various filters"""
    try:
        tag_list = tags.split(',') if tags else None
        return news_manager.search_news(
            keyword=keyword,
            date_from=date_from,
            date_to=date_to,
            sentiment=sentiment,
            source=source,
            tags=tag_list,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/news/{news_id}")
def get_news(news_id: int):
    """Get a single news entry by ID"""
    try:
        news = news_manager.get_news(news_id)
        if not news:
            raise HTTPException(status_code=404, detail="News not found")
        return news
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/news")
def get_all_news(limit: int = Query(default=100, le=500), offset: int = Query(default=0)):
    """Get all news entries with pagination"""
    try:
        return news_manager.get_all_news(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/news/{news_id}")
def update_news(news_id: int, updates: NewsUpdate):
    """Update a news entry"""
    try:
        update_dict = {k: v for k, v in updates.dict().items() if v is not None}
        if not update_dict:
            raise HTTPException(status_code=400, detail="No fields to update")
        return news_manager.update_news(news_id, update_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/news/{news_id}")
def delete_news(news_id: int):
    """Delete a news entry"""
    try:
        success = news_manager.delete_news(news_id)
        if not success:
            raise HTTPException(status_code=404, detail="News not found")
        return {"message": "News deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
