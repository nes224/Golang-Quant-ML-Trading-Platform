from typing import Dict, Optional
import pandas as pd
from datetime import datetime

class RiskManager:
    """
    Manages risk calculations for trading positions
    """
    
    def __init__(self, account_balance: float, config: Dict):
        self.account_balance = account_balance
        self.config = config
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.peak_balance = account_balance
        
    def update_balance(self, new_balance: float):
        """Update account balance"""
        self.account_balance = new_balance
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
    
    def can_trade(self, symbol: str = None) -> tuple[bool, str]:
        """
        Check if trading is allowed based on risk limits
        
        Returns:
            (can_trade: bool, reason: str)
        """
        # Check daily loss limit
        daily_loss_limit = self.account_balance * (self.config['daily_loss_limit_percent'] / 100)
        if self.daily_pnl < -daily_loss_limit:
            return False, f"Daily loss limit hit: ${abs(self.daily_pnl):.2f}"
        
        # Check max drawdown
        current_drawdown = ((self.peak_balance - self.account_balance) / self.peak_balance) * 100
        if current_drawdown > self.config['max_drawdown_percent']:
            return False, f"Max drawdown exceeded: {current_drawdown:.2f}%"
        
        # Check consecutive losses
        if self.consecutive_losses >= self.config['max_consecutive_losses']:
            return False, f"Max consecutive losses: {self.consecutive_losses}"
        
        return True, "OK"
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        sl_price: float,
        risk_percent: Optional[float] = None
    ) -> Dict:
        """
        Calculate position size based on risk parameters
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            sl_price: Stop loss price
            risk_percent: Risk percentage (overrides config if provided)
        
        Returns:
            Dictionary with position sizing details
        """
        if risk_percent is None:
            risk_percent = self.config.get('default_risk_percent', 1.0)
        
        # Calculate risk amount in dollars
        risk_amount = self.account_balance * (risk_percent / 100)
        
        # Calculate SL distance
        sl_distance = abs(entry_price - sl_price)
        
        # Calculate position size
        # For stocks/crypto: position_size = risk_amount / sl_distance
        # For forex: need to account for pip value
        
        if "USD" in symbol or "BTC" in symbol:
            # Crypto or USD pairs
            position_size = risk_amount / sl_distance
        else:
            # Forex or other instruments
            # Simplified calculation (adjust based on actual instrument)
            pip_value = 10  # Assume $10 per pip for standard lot
            sl_distance_pips = sl_distance * 10000  # Convert to pips
            position_size = risk_amount / (sl_distance_pips * pip_value)
        
        # Round to appropriate precision
        position_size = round(position_size, 4)
        
        return {
            'position_size': position_size,
            'risk_amount': risk_amount,
            'sl_distance': sl_distance,
            'risk_percent': risk_percent
        }
    
    def calculate_sl_tp(
        self,
        df: pd.DataFrame,
        direction: str,
        entry_price: float,
        sr_zones: list = None
    ) -> Dict:
        """
        Calculate Stop Loss and Take Profit levels
        
        Args:
            df: DataFrame with price data and indicators
            direction: 'BUY' or 'SELL'
            entry_price: Entry price
            sr_zones: List of S/R zones (optional)
        
        Returns:
            Dictionary with SL and TP levels
        """
        last_row = df.iloc[-1]
        atr = last_row.get('ATR', 0)
        
        sl_method = self.config.get('sl_method', 'atr')
        sl_atr_multiplier = self.config.get('sl_atr_multiplier', 2.0)
        tp_rr_ratio = self.config.get('tp_rr_ratio', 2.0)
        
        # Calculate Stop Loss
        if sl_method == 'atr':
            sl_distance = atr * sl_atr_multiplier
            if direction == 'BUY':
                sl_price = entry_price - sl_distance
            else:  # SELL
                sl_price = entry_price + sl_distance
                
        elif sl_method == 'sr_zone' and sr_zones:
            # Use nearest S/R zone
            if direction == 'BUY':
                # SL below nearest support
                support_zones = [z for z in sr_zones if z['type'] == 'support' and z['level'] < entry_price]
                if support_zones:
                    nearest_support = min(support_zones, key=lambda x: abs(x['level'] - entry_price))
                    sl_price = nearest_support['bottom'] - (atr * 0.5)  # Slightly below zone
                else:
                    sl_price = entry_price - (atr * sl_atr_multiplier)
            else:  # SELL
                # SL above nearest resistance
                resistance_zones = [z for z in sr_zones if z['type'] == 'resistance' and z['level'] > entry_price]
                if resistance_zones:
                    nearest_resistance = min(resistance_zones, key=lambda x: abs(x['level'] - entry_price))
                    sl_price = nearest_resistance['top'] + (atr * 0.5)  # Slightly above zone
                else:
                    sl_price = entry_price + (atr * sl_atr_multiplier)
        else:
            # Default to ATR
            sl_distance = atr * sl_atr_multiplier
            if direction == 'BUY':
                sl_price = entry_price - sl_distance
            else:
                sl_price = entry_price + sl_distance
        
        # Calculate Take Profit based on RR ratio
        sl_distance = abs(entry_price - sl_price)
        tp_distance = sl_distance * tp_rr_ratio
        
        if direction == 'BUY':
            tp_price = entry_price + tp_distance
        else:  # SELL
            tp_price = entry_price - tp_distance
        
        return {
            'sl_price': round(sl_price, 2),
            'tp_price': round(tp_price, 2),
            'sl_distance': round(sl_distance, 2),
            'tp_distance': round(tp_distance, 2),
            'rr_ratio': tp_rr_ratio
        }
    
    def record_trade_result(self, profit_loss: float):
        """
        Record trade result and update risk metrics
        
        Args:
            profit_loss: Profit or loss in dollars
        """
        self.daily_pnl += profit_loss
        self.account_balance += profit_loss
        
        if profit_loss < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
            
        # Update peak balance
        if self.account_balance > self.peak_balance:
            self.peak_balance = self.account_balance
    
    def reset_daily_stats(self):
        """Reset daily statistics (call at start of new day)"""
        self.daily_pnl = 0.0
    
    def get_risk_status(self) -> Dict:
        """Get current risk status"""
        current_drawdown = ((self.peak_balance - self.account_balance) / self.peak_balance) * 100
        daily_loss_limit = self.account_balance * (self.config['daily_loss_limit_percent'] / 100)
        
        return {
            'account_balance': self.account_balance,
            'peak_balance': self.peak_balance,
            'daily_pnl': self.daily_pnl,
            'daily_loss_limit': daily_loss_limit,
            'current_drawdown_percent': current_drawdown,
            'max_drawdown_percent': self.config['max_drawdown_percent'],
            'consecutive_losses': self.consecutive_losses,
            'max_consecutive_losses': self.config['max_consecutive_losses'],
            'can_trade': self.can_trade()[0]
        }
