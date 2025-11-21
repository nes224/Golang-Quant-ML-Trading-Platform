"""
Risk Management Module
Calculates position size, stop loss, and take profit based on account balance and risk parameters.
"""

def calculate_stop_loss(entry_price, atr, direction, multiplier=2.0):
    """
    Calculate stop loss based on ATR (Average True Range).
    
    Args:
        entry_price: Entry price for the trade
        atr: Average True Range value
        direction: 'BUY' or 'SELL'
        multiplier: ATR multiplier for stop distance (default 2.0)
    
    Returns:
        Stop loss price
    """
    sl_distance = atr * multiplier
    
    if direction.upper() == 'BUY':
        stop_loss = entry_price - sl_distance
    else:  # SELL
        stop_loss = entry_price + sl_distance
    
    return round(stop_loss, 2)


def calculate_take_profit(entry_price, stop_loss, risk_reward_ratio=2.0):
    """
    Calculate take profit based on risk:reward ratio.
    
    Args:
        entry_price: Entry price for the trade
        stop_loss: Stop loss price
        risk_reward_ratio: Ratio of reward to risk (default 2.0 = 1:2)
    
    Returns:
        Take profit price
    """
    sl_distance = abs(entry_price - stop_loss)
    tp_distance = sl_distance * risk_reward_ratio
    
    if entry_price > stop_loss:  # BUY
        take_profit = entry_price + tp_distance
    else:  # SELL
        take_profit = entry_price - tp_distance
    
    return round(take_profit, 2)


def calculate_position_size(account_balance, risk_percent, entry_price, stop_loss_price, contract_size=100):
    """
    Calculate position size based on account balance and risk percentage.
    
    Args:
        account_balance: Total account balance
        risk_percent: Percentage of account to risk (e.g., 1.0 for 1%)
        entry_price: Entry price for the trade
        stop_loss_price: Stop loss price
        contract_size: Contract size (100 oz for Gold, 100,000 for Forex)
    
    Returns:
        dict with position_size (lots), risk_amount, and pip_value
    """
    # Calculate risk amount in dollars
    risk_amount = account_balance * (risk_percent / 100)
    
    # Calculate distance to stop loss
    sl_distance = abs(entry_price - stop_loss_price)
    
    # Calculate position size in lots
    # For Gold: 1 lot = 100 oz, so $1 move = $100
    pip_value = contract_size  # $100 per $1 move for Gold
    position_size = risk_amount / (sl_distance * pip_value)
    
    # Round to 2 decimal places (0.01 lot minimum)
    position_size = round(position_size, 2)
    
    # Ensure minimum position size
    if position_size < 0.01:
        position_size = 0.01
    
    return {
        "position_size": position_size,
        "risk_amount": round(risk_amount, 2),
        "sl_distance": round(sl_distance, 2),
        "pip_value": pip_value
    }


def get_risk_parameters(symbol, timeframe, account_balance, risk_percent, direction, entry_price=None, 
                       atr_multiplier=2.0, risk_reward_ratio=2.0):
    """
    Get complete risk management parameters for a trade.
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe for analysis
        account_balance: Total account balance
        risk_percent: Percentage of account to risk
        direction: 'BUY' or 'SELL'
        entry_price: Optional entry price (uses current if not provided)
        atr_multiplier: ATR multiplier for stop loss
        risk_reward_ratio: Risk:Reward ratio for take profit
    
    Returns:
        dict with all risk parameters
    """
    from data_loader import fetch_data
    from analysis import calculate_indicators
    
    # Fetch data and calculate ATR
    if timeframe == "1m":
        period = "5d"
    elif timeframe in ["5m", "15m", "30m"]:
        period = "1mo"
    else:
        period = "1y"
    
    df = fetch_data(symbol, period=period, interval=timeframe)
    
    if df is None or df.empty:
        return {"error": "Unable to fetch data"}
    
    df = calculate_indicators(df)
    last_row = df.iloc[-1]
    
    # Use current price if entry not provided
    if entry_price is None:
        entry_price = last_row['Close']
    
    atr = last_row['ATR']
    
    # Calculate SL and TP
    stop_loss = calculate_stop_loss(entry_price, atr, direction, atr_multiplier)
    take_profit = calculate_take_profit(entry_price, stop_loss, risk_reward_ratio)
    
    # Calculate position size
    position_info = calculate_position_size(account_balance, risk_percent, entry_price, stop_loss)
    
    # Calculate potential profit/loss
    potential_loss = position_info['risk_amount']
    potential_profit = potential_loss * risk_reward_ratio
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": direction.upper(),
        "entry_price": round(entry_price, 2),
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "atr": round(atr, 2),
        "position_size_lots": position_info['position_size'],
        "risk_amount": potential_loss,
        "potential_profit": round(potential_profit, 2),
        "risk_reward_ratio": f"1:{risk_reward_ratio}",
        "account_balance": account_balance,
        "risk_percent": risk_percent
    }
