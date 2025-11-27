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
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    # Auto-import data from other OS
    try:
        from app.services.db_sync import auto_import_on_startup
        auto_import_on_startup()
    except Exception as e:
        print(f"[WARNING] Auto-import failed: {e}")
    
    # Start background task for real-time data broadcast
    asyncio.create_task(broadcast_market_data())
    print("[OK] Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    # Auto-export database before shutdown
    try:
        from app.services.db_sync import auto_export_on_shutdown
        auto_export_on_shutdown()
    except Exception as e:
        print(f"[WARNING] Auto-export failed: {e}")
    
    print("[OK] Application shutdown complete")

@app.get("/")
def read_root():
    return {
        "message": "XAU/USD Trading Bot API",
        "version": "2.0.0",
        "docs": "/docs"
    }
