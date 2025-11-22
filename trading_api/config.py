import os

class Config:
    # Data Source: 'YAHOO' or 'MT5'
    DATA_SOURCE = os.getenv("DATA_SOURCE", "MT5")
    
    # MetaTrader 5 Settings (if applicable)
    MT5_LOGIN = int(os.getenv("MT5_LOGIN", "206646872"))
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "245026772451Pn@")
    MT5_SERVER = os.getenv("MT5_SERVER", "Exness-MT5Trial7")
    MT5_PATH = os.getenv("MT5_PATH", "") # Path to terminal64.exe if not auto-detected
