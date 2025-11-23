import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_loader import fetch_data
import asyncio

class DataManager:
    def __init__(self, symbol="GC=F"):
        self.symbol = symbol
        self.timeframes = ["4h", "1h", "30m", "15m", "5m"]
        self.data = {} # Stores DataFrame for each timeframe
        self.last_update_time = {} # Stores last update timestamp for each TF
        self.initialized = False
        
    async def initialize(self):
        """
        Fetches initial historical data for all timeframes.
        """
        print(f"Initializing DataManager for {self.symbol}...")
        
        # Fetch data sequentially (or parallel if we move fetch_data to async)
        # Since fetch_data is sync, we run it in thread pool to not block
        loop = asyncio.get_event_loop()
        
        tasks = []
        for tf in self.timeframes:
            tasks.append(loop.run_in_executor(None, self._fetch_initial_data, tf))
            
        results = await asyncio.gather(*tasks)
        
        for i, tf in enumerate(self.timeframes):
            if results[i] is not None and not results[i].empty:
                self.data[tf] = results[i]
                # Date is in index, not column
                self.last_update_time[tf] = results[i].index[-1]
                print(f"Loaded {tf}: {len(results[i])} bars")
            else:
                print(f"Failed to load data for {tf}")
                # Initialize empty DF structure if failed
                self.data[tf] = pd.DataFrame(columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
                
        self.initialized = True
        print("DataManager initialized.")

    def _fetch_initial_data(self, tf):
        # Logic from main.py to determine period
        if tf == "1m":
            period = "5d"
        elif tf in ["5m", "15m", "30m"]:
            period = "1mo"
        else:
            period = "3mo"
            
        return fetch_data(self.symbol, period=period, interval=tf)

    def update_tick(self, price, timestamp=None):
        """
        Updates the latest candle with the new tick price.
        Handles new candle creation if time boundary is crossed.
        """
        if not self.initialized:
            return

        if timestamp is None:
            timestamp = pd.Timestamp.now()
        else:
            timestamp = pd.Timestamp(timestamp)

        for tf in self.timeframes:
            if tf not in self.data or self.data[tf].empty:
                continue
                
            df = self.data[tf]
            last_row = df.iloc[-1]
            last_date = last_row['Date']
            
            # Check if we need a new candle
            is_new_candle = self._check_new_candle(tf, last_date, timestamp)
            
            if is_new_candle:
                # Create new candle
                new_row = {
                    'Date': self._get_candle_start_time(tf, timestamp),
                    'Open': price,
                    'High': price,
                    'Low': price,
                    'Close': price,
                    'Volume': 0 # Volume info not available in simple tick update
                }
                # Append new row
                # Using concat is slow, but for 1 row it's acceptable. 
                # For extreme performance we might use a list of dicts and convert to DF only when needed,
                # but for now keeping DF structure is easier for integration.
                new_df = pd.DataFrame([new_row])
                self.data[tf] = pd.concat([df, new_df], ignore_index=True)
                
                # Trim old data to keep memory usage stable (keep last 1000 bars)
                if len(self.data[tf]) > 2000:
                    self.data[tf] = self.data[tf].iloc[-1000:].reset_index(drop=True)
                    
            else:
                # Update current candle
                idx = df.index[-1]
                df.at[idx, 'Close'] = price
                df.at[idx, 'High'] = max(df.at[idx, 'High'], price)
                df.at[idx, 'Low'] = min(df.at[idx, 'Low'], price)
                # Volume update would go here if we had tick volume

    def get_data(self, tf):
        """Returns the current DataFrame for a timeframe."""
        return self.data.get(tf)

    def _check_new_candle(self, tf, last_date, current_time):
        """
        Determines if a new candle should be created based on timeframe.
        """
        # Simple logic: check if current_time is in the next interval
        # This assumes last_date is the START time of the candle
        
        delta = current_time - last_date
        
        if tf == "1m":
            return delta >= timedelta(minutes=1)
        elif tf == "5m":
            return delta >= timedelta(minutes=5)
        elif tf == "15m":
            return delta >= timedelta(minutes=15)
        elif tf == "30m":
            return delta >= timedelta(minutes=30)
        elif tf == "1h":
            return delta >= timedelta(hours=1)
        elif tf == "4h":
            return delta >= timedelta(hours=4)
        elif tf == "1d":
            return delta >= timedelta(days=1)
        return False

    def _get_candle_start_time(self, tf, current_time):
        """
        Aligns timestamp to the start of the timeframe candle.
        """
        if tf == "1m":
            return current_time.floor('1min')
        elif tf == "5m":
            return current_time.floor('5min')
        elif tf == "15m":
            return current_time.floor('15min')
        elif tf == "30m":
            return current_time.floor('30min')
        elif tf == "1h":
            return current_time.floor('1h')
        elif tf == "4h":
            # 4h alignment is tricky (00, 04, 08...), floor('4h') works in pandas recent versions
            # or we can use custom logic
            hour = current_time.hour
            start_hour = hour - (hour % 4)
            return current_time.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        elif tf == "1d":
            return current_time.floor('1d')
        return current_time
