from fastapi import APIRouter
from app.api.v1.endpoints import market, journal, checklist, news, risk, reference, websocket

api_router = APIRouter()

api_router.include_router(market.router, tags=["Market Data"])
api_router.include_router(risk.router, tags=["Risk Management"])
api_router.include_router(journal.router, tags=["Journal"])
api_router.include_router(checklist.router, tags=["Checklist"])
api_router.include_router(news.router, prefix="/api/v1", tags=["News"])
api_router.include_router(reference.router, prefix="/api", tags=["Reference Indicators"])
api_router.include_router(websocket.router, tags=["WebSocket"])
