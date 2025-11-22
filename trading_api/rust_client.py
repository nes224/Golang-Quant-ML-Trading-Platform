import requests
from typing import List, Dict, Optional
import pandas as pd

class RustAnalysisClient:
    """Client for communicating with Rust Analysis API"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.timeout = 5  # seconds
    
    def health_check(self) -> bool:
        """Check if Rust service is running"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            return response.status_code == 200
        except:
            return False
    
    def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """
        Calculate technical indicators using Rust service.
        
        Args:
            df: DataFrame with OHLC data
        
        Returns:
            Dict with ema_50, ema_200, rsi, atr arrays
        """
        try:
            payload = {
                "prices": df['Close'].tolist(),
                "high": df['High'].tolist(),
                "low": df['Low'].tolist(),
                "close": df['Close'].tolist()
            }
            
            response = requests.post(
                f"{self.base_url}/calculate/indicators",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error calling Rust indicators API: {e}")
            return None
    
    def detect_patterns(self, df: pd.DataFrame) -> Dict:
        """
        Detect candlestick patterns using Rust service.
        
        Args:
            df: DataFrame with OHLC data
        
        Returns:
            Dict with pattern detection results
        """
        try:
            ohlc = []
            for _, row in df.iterrows():
                ohlc.append({
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close'])
                })
            
            payload = {"ohlc": ohlc}
            
            response = requests.post(
                f"{self.base_url}/detect/patterns",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error calling Rust patterns API: {e}")
            return None

# Global client instance
rust_client = RustAnalysisClient()
