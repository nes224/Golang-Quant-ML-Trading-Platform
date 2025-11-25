"""
Configuration for external data sources (DXY, US10Y)
"""

# Cache duration in seconds
DXY_CACHE_DURATION = 300  # 5 minutes
US10Y_CACHE_DURATION = 300  # 5 minutes

# Retry settings
MAX_RETRIES = 2
RETRY_DELAY = 1  # seconds

# Error suppression
SUPPRESS_ERRORS = True  # Set to False for debugging

# Fallback data (used when fetch fails)
FALLBACK_DXY = {
    "symbol": "DXY",
    "error": "Service temporarily unavailable",
    "trend": "UNKNOWN",
    "price": 0.0,
    "change_percent": 0.0,
    "timeframe": "1d"
}

FALLBACK_US10Y = {
    "symbol": "US10Y",
    "error": "Service temporarily unavailable",
    "trend": "UNKNOWN",
    "price": 0.0,
    "change_percent": 0.0,
    "timeframe": "1d"
}
