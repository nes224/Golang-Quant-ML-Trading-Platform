from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.config import Config
from app.services.websocket_manager import manager
from app.services.market_stream import broadcast_market_data
import asyncio

app = FastAPI(
    title="XAU/USD Trading Analysis Bot",
    description="API for analyzing Gold (XAU/USD) market data with candlestick charts.",
    version="2.0.0"
)

# Enable CORS for Next.js Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    # Start background task for real-time data broadcast
    asyncio.create_task(broadcast_market_data())
    print("[OK] Application started successfully")

@app.get("/")
def read_root():
    return {
        "message": "XAU/USD Trading Bot API",
        "version": "2.0.0",
        "docs": "/docs"
    }
