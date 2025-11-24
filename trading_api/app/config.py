import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Data Source: 'YAHOO', 'MT5', 'FINNHUB', or 'TWELVE'
    DATA_SOURCE = os.getenv("DATA_SOURCE", "MT5")
    
    # MetaTrader 5 Settings (if applicable)
    mt5_login_str = os.getenv("MT5_LOGIN", "")
    MT5_LOGIN = int(mt5_login_str) if mt5_login_str.strip() else 0
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER = os.getenv("MT5_SERVER", "")
    MT5_PATH = os.getenv("MT5_PATH", "") # Path to terminal64.exe if not auto-detected
    
    # Finnhub Settings (if applicable)
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
    
    # Twelve Data Settings (if applicable)
    TWELVE_API_KEY = os.getenv("TWELVE_API_KEY", "")
