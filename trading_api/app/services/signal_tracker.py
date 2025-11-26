"""
Signal Tracker Service - Incremental Signal Updates

This service tracks signals and only recalculates when new candles form,
reducing CPU usage by ~99% compared to full recalculation every second.
"""

from typing import Dict, List, Tuple
from datetime import datetime
import pandas as pd


class SignalTracker:
    """
    Track signals and only recalculate when new candle forms
    
    Usage:
        tracker = SignalTracker()
        signals_updated, signals = tracker.update_signals(candles, timeframe)
        
        if signals_updated:
            # New candle! Send full update
        else:
            # Just price update, use cached signals
    """
    
    def __init__(self):
        self.last_candle_count = 0
        self.cached_signals = {}
        self.last_update_time = None
    
    def should_recalculate(self, candles: List[Dict]) -> bool:
        """
        Check if we need to recalculate signals
        
        Args:
            candles: List of candle dictionaries
            
        Returns:
            True if new candle formed, False otherwise
        """
        return len(candles) > self.last_candle_count
    
    def update_signals(self, candles: List[Dict], timeframe: str) -> Tuple[bool, Dict]:
        """
        Update signals if new candle formed
        
        Args:
            candles: List of candle dictionaries
            timeframe: Timeframe string (e.g., "1h", "15m")
            
        Returns:
            (signals_updated, signals): Tuple of (bool, dict)
                - signals_updated: True if signals were recalculated
                - signals: Dictionary of all signals
        """
        if self.should_recalculate(candles):
            # New candle! Recalculate all signals
            print(f"[SIGNAL_TRACKER] New candle detected, recalculating signals for {timeframe}")
            
            self.cached_signals = self._calculate_all_signals(candles, timeframe)
            self.last_candle_count = len(candles)
            self.last_update_time = datetime.now()
            
            return True, self.cached_signals
        
        # No new candle, return cached signals
        return False, self.cached_signals
    
    def _calculate_all_signals(self, candles: List[Dict], timeframe: str) -> Dict:
        """
        Calculate all signals for given candles
        
        Args:
            candles: List of candle dictionaries
            timeframe: Timeframe string
            
        Returns:
            Dictionary containing all signals
        """
        # Import here to avoid circular imports
        from app.services.analysis.levels import identify_pivot_points, identify_key_levels
        from app.services.analysis.fvg import detect_fvg, detect_break_signal
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(candles)
        
        # Normalize column names (MT5 uses lowercase, Yahoo uses Capitalized)
        column_mapping = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # Ensure datetime index
        if 'time' in df.columns:
            try:
                df['time'] = pd.to_datetime(df['time'], format='mixed')
            except ValueError:
                # Fallback if mixed fails (e.g. for very specific formats)
                df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)
        
        # Adaptive parameters based on timeframe
        if timeframe in ['1m', '5m']:
            left_bars = 3
            right_bars = 3
        elif timeframe in ['15m', '30m']:
            left_bars = 5
            right_bars = 5
        else:
            left_bars = 7
            right_bars = 7
        
        # Calculate signals
        signals = {}
        
        try:
            # 1. Pivot Points
            df_with_pivots = identify_pivot_points(df, left_bars=left_bars, right_bars=right_bars)
            pivot_points = self._extract_pivot_points(df_with_pivots)
            signals['pivot_points'] = pivot_points
            
            # 2. Key Levels
            key_levels = identify_key_levels(df, bin_width=0.003, min_touches=3)
            signals['key_levels'] = key_levels
            
            # 3. FVG Zones
            df_with_fvg = detect_fvg(df, lookback_period=10, body_multiplier=1.5)
            fvg_zones = self._extract_fvg_zones(df_with_fvg)
            signals['fvg_zones'] = fvg_zones
            
            # 4. Break Signals
            df_with_signals = detect_break_signal(df_with_fvg)
            break_signals = self._extract_break_signals(df_with_signals)
            signals['break_signals'] = break_signals
            
        except Exception as e:
            print(f"[SIGNAL_TRACKER] Error calculating signals: {e}")
            import traceback
            traceback.print_exc()
            
            # Return empty signals on error
            signals = {
                'pivot_points': [],
                'key_levels': [],
                'fvg_zones': [],
                'break_signals': []
            }
        
        return signals
    
    def _extract_pivot_points(self, df: pd.DataFrame) -> List[Dict]:
        """Extract pivot points from DataFrame"""
        pivot_points = []
        
        if 'pivot_type' not in df.columns:
            return pivot_points
        
        df_pivots = df[df['pivot_type'].astype(str) != ''].copy()
        
        for idx, row in df_pivots.iterrows():
            pivot_points.append({
                'time': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                'price': float(row.get('Close', row.get('close', 0))),
                'type': str(row['pivot_type'])
            })
        
        return pivot_points
    
    def _extract_fvg_zones(self, df: pd.DataFrame) -> List[Dict]:
        """Extract FVG zones from DataFrame"""
        fvg_zones = []
        
        if 'fvg_type' not in df.columns:
            return fvg_zones
        
        df_fvg = df[df['fvg_type'].notna()].copy()
        
        for idx, row in df_fvg.iterrows():
            fvg_zones.append({
                'start_time': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                'end_time': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                'low': float(row.get('fvg_low', 0)),
                'high': float(row.get('fvg_high', 0)),
                'type': str(row['fvg_type'])
            })
        
        return fvg_zones
    
    def _extract_break_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Extract break signals from DataFrame"""
        break_signals = []
        
        if 'break_signal' not in df.columns:
            return break_signals
        
        df_signals = df[df['break_signal'] != 0].copy()
        
        for idx, row in df_signals.iterrows():
            signal_type = 'buy' if row['break_signal'] == 2 else 'sell'
            break_signals.append({
                'time': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                'price': float(row.get('Close', row.get('close', 0))),
                'type': signal_type
            })
        
        return break_signals
    
    def get_stats(self) -> Dict:
        """Get tracker statistics"""
        return {
            'last_candle_count': self.last_candle_count,
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'cached_signals_count': {
                'pivot_points': len(self.cached_signals.get('pivot_points', [])),
                'fvg_zones': len(self.cached_signals.get('fvg_zones', [])),
                'break_signals': len(self.cached_signals.get('break_signals', []))
            }
        }
