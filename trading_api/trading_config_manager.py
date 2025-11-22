import yaml
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class SymbolConfig:
    """Configuration for a single trading symbol"""
    symbol: str
    enabled: bool
    risk_percent: float
    max_position_size: float
    timeframes: List[str]

@dataclass
class GlobalSettings:
    """Global trading settings"""
    max_concurrent_trades: int
    max_trades_per_symbol: int
    daily_loss_limit_percent: float
    max_drawdown_percent: float
    default_risk_percent: float
    default_rr_ratio: float
    sl_method: str
    sl_atr_multiplier: float
    tp_rr_ratio: float
    use_trailing_stop: bool
    trailing_stop_activation: float
    trailing_stop_distance: float
    max_consecutive_losses: int
    rapid_drawdown_threshold: float

class TradingConfig:
    """
    Manages trading configuration from YAML file
    """
    
    def __init__(self, config_path: str = "trading_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"❌ Config file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            print(f"❌ Error parsing config file: {e}")
            raise
    
    def get_enabled_symbols(self) -> List[SymbolConfig]:
        """Get list of enabled trading symbols"""
        symbols = []
        for sym_config in self.config.get('symbols', []):
            if sym_config.get('enabled', False):
                symbols.append(SymbolConfig(
                    symbol=sym_config['symbol'],
                    enabled=sym_config['enabled'],
                    risk_percent=sym_config.get('risk_percent', 1.0),
                    max_position_size=sym_config.get('max_position_size', 1.0),
                    timeframes=sym_config.get('timeframes', ['4h', '1h'])
                ))
        return symbols
    
    def get_symbol_config(self, symbol: str) -> Optional[SymbolConfig]:
        """Get configuration for a specific symbol"""
        for sym_config in self.config.get('symbols', []):
            if sym_config['symbol'] == symbol:
                return SymbolConfig(
                    symbol=sym_config['symbol'],
                    enabled=sym_config.get('enabled', False),
                    risk_percent=sym_config.get('risk_percent', 1.0),
                    max_position_size=sym_config.get('max_position_size', 1.0),
                    timeframes=sym_config.get('timeframes', ['4h', '1h'])
                )
        return None
    
    def get_global_settings(self) -> GlobalSettings:
        """Get global trading settings"""
        gs = self.config.get('global_settings', {})
        return GlobalSettings(
            max_concurrent_trades=gs.get('max_concurrent_trades', 5),
            max_trades_per_symbol=gs.get('max_trades_per_symbol', 2),
            daily_loss_limit_percent=gs.get('daily_loss_limit_percent', 5.0),
            max_drawdown_percent=gs.get('max_drawdown_percent', 10.0),
            default_risk_percent=gs.get('default_risk_percent', 1.0),
            default_rr_ratio=gs.get('default_rr_ratio', 2.0),
            sl_method=gs.get('sl_method', 'atr'),
            sl_atr_multiplier=gs.get('sl_atr_multiplier', 2.0),
            tp_rr_ratio=gs.get('tp_rr_ratio', 2.0),
            use_trailing_stop=gs.get('use_trailing_stop', False),
            trailing_stop_activation=gs.get('trailing_stop_activation', 1.0),
            trailing_stop_distance=gs.get('trailing_stop_distance', 0.5),
            max_consecutive_losses=gs.get('max_consecutive_losses', 3),
            rapid_drawdown_threshold=gs.get('rapid_drawdown_threshold', 3.0)
        )
    
    def is_paper_trading(self) -> bool:
        """Check if paper trading mode is enabled"""
        return self.config.get('paper_trading', {}).get('enabled', True)
    
    def get_paper_trading_balance(self) -> float:
        """Get initial balance for paper trading"""
        return self.config.get('paper_trading', {}).get('initial_balance', 100.0)
    
    def get_broker_type(self) -> str:
        """Get broker type"""
        return self.config.get('broker', {}).get('type', 'paper')
    
    def get_mt5_settings(self) -> Dict:
        """Get MT5 broker settings"""
        return self.config.get('broker', {}).get('mt5', {})
    
    def reload(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        print("✅ Configuration reloaded")


# Global config instance
_config = None

def get_trading_config() -> TradingConfig:
    """Get or create global TradingConfig instance"""
    global _config
    if _config is None:
        config_path = os.path.join(os.path.dirname(__file__), 'trading_config.yaml')
        _config = TradingConfig(config_path)
    return _config
