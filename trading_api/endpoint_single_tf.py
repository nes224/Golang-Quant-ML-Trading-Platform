@app.get("/signal/{timeframe}")
def get_signal_single_timeframe(
    timeframe: str,
    symbol: str = Query("GC=F", description="Symbol to analyze")
):
    """
    Returns analysis for a single timeframe only.
    Useful for manual refresh of specific timeframes.
    """
    from sr_zones import identify_sr_zones, get_nearest_sr
    from analysis import identify_fvg, identify_order_blocks, identify_pin_bar, identify_rejection
    
    global data_manager
    
    # Validate timeframe
    valid_timeframes = ["1d", "4h", "1h", "30m", "15m", "5m", "1m"]
    if timeframe not in valid_timeframes:
        return {"error": f"Invalid timeframe. Must be one of: {valid_timeframes}"}
    
    # Get global trend from 4h
    global_trend = "NEUTRAL"
    df_h4_bias = None
    
    if data_manager and data_manager.symbol == symbol and data_manager.initialized:
        df_h4_bias = data_manager.get_data("4h")
    else:
        df_h4_bias = fetch_data(symbol, period="3mo", interval="4h")
        
    if df_h4_bias is not None and not df_h4_bias.empty:
        if 'EMA_200' not in df_h4_bias.columns:
            df_h4_bias = calculate_indicators(df_h4_bias)
            
        last_h4 = df_h4_bias.iloc[-1]
        if last_h4['Close'] > last_h4['EMA_200']:
            global_trend = "UP"
        else:
            global_trend = "DOWN"
    
    # Fetch data for this timeframe
    df = None
    if data_manager and data_manager.initialized:
        is_match = (data_manager.symbol == symbol) or \
                   (data_manager.symbol == "XAUUSD" and symbol == "GC=F") or \
                   (data_manager.symbol == "GC=F" and symbol == "XAUUSD")
                   
        if is_match:
            df = data_manager.get_data(timeframe)
            if df is not None:
                df = df.copy()
    
    if df is None:
        if timeframe == "1m":
            period = "5d"
        elif timeframe in ["5m", "15m", "30m"]:
            period = "1mo"
        elif timeframe in ["1h", "4h"]:
            period = "3mo"
        else:
            period = "3mo"
        df = fetch_data(symbol, period=period, interval=timeframe)
    
    if df is None or df.empty:
        return {"error": "Data not available", "timeframe": timeframe}
        
    # Limit to last 500 candles
    if len(df) > 500:
        df = df.tail(500).copy()
        
    # Calculate all indicators
    df = calculate_indicators(df)
    df = identify_structure(df)
    df, sr_zones = identify_sr_zones(df)
    df = identify_fvg(df)
    df = identify_order_blocks(df)
    df = identify_pin_bar(df)
    df = identify_rejection(df)
    df = check_signals(df)
    
    last_row = df.iloc[-1]
    
    # Determine trend
    if last_row['Close'] > last_row['EMA_200']:
        trend = "UP"
    elif last_row['Close'] < last_row['EMA_200']:
        trend = "DOWN"
    else:
        trend = "SIDEWAY"
    
    # Determine signal
    tech_signal = last_row['Signal']
    signal_map = {1: "BUY", -1: "SELL", 0: "WAIT"}
    final_signal = signal_map.get(tech_signal, "WAIT")
    
    # SMC features
    recent_df = df.tail(3)
    smc_context = []
    if recent_df['FVG_Bullish'].any(): smc_context.append("Bullish FVG")
    if recent_df['FVG_Bearish'].any(): smc_context.append("Bearish FVG")
    if recent_df['OB_Bullish'].any(): smc_context.append("Bullish OB")
    if recent_df['OB_Bearish'].any(): smc_context.append("Bearish OB")
    
    # Price Action patterns
    pa_patterns = []
    if last_row.get('Hammer', False): pa_patterns.append("Hammer")
    if last_row.get('Inverted_Hammer', False): pa_patterns.append("Inverted Hammer")
    if last_row.get('Hanging_Man', False): pa_patterns.append("Hanging Man")
    if last_row.get('Dragonfly_Doji', False): pa_patterns.append("Dragonfly Doji")
    if last_row.get('Gravestone_Doji', False): pa_patterns.append("Gravestone Doji")
    if last_row.get('Bullish_Engulfing', False): pa_patterns.append("Bullish Engulfing")
    if last_row.get('Bearish_Engulfing', False): pa_patterns.append("Bearish Engulfing")
    if last_row.get('Morning_Star', False): pa_patterns.append("Morning Star")
    if last_row.get('Evening_Star', False): pa_patterns.append("Evening Star")
    if last_row.get('Pin_Bar_Bullish', False): pa_patterns.append("Bullish Pin Bar")
    if last_row.get('Pin_Bar_Bearish', False): pa_patterns.append("Bearish Pin Bar")
    if last_row.get('Rejection_Bullish', False): pa_patterns.append("Bullish Rejection")
    if last_row.get('Rejection_Bearish', False): pa_patterns.append("Bearish Rejection")
    
    smc_text = ", ".join(smc_context) if smc_context else "None"
    pa_text = ", ".join(pa_patterns) if pa_patterns else "None"
    
    # Format S/R zones
    nearest_support = get_nearest_sr(df, sr_zones, 'support')
    nearest_resistance = get_nearest_sr(df, sr_zones, 'resistance')
    
    sr_text = []
    if nearest_support:
        s_min = nearest_support.get('bottom', nearest_support['level'])
        s_max = nearest_support.get('top', nearest_support['level'])
        sr_text.append(f"S: {s_min}-{s_max} ({nearest_support['strength']}x)")
        
    if nearest_resistance:
        r_min = nearest_resistance.get('bottom', nearest_resistance['level'])
        r_max = nearest_resistance.get('top', nearest_resistance['level'])
        sr_text.append(f"R: {r_min}-{r_max} ({nearest_resistance['strength']}x)")
        
    sr_display = ", ".join(sr_text) if sr_text else "None"
    
    # Extract FVG zones
    fvg_zones_display = []
    if hasattr(df, 'attrs') and 'fvg_zones' in df.attrs:
        for zone in df.attrs['fvg_zones'][-3:]:
            zone_type = "🟢" if zone['zone_type'] == 'bullish' else "🔴"
            fvg_zones_display.append(f"{zone_type} {zone['bottom']:.2f}-{zone['top']:.2f}")
    
    # Extract OB zones
    ob_zones_display = []
    if hasattr(df, 'attrs') and 'ob_zones' in df.attrs:
        for zone in df.attrs['ob_zones'][-3:]:
            zone_type = "🟢" if zone['zone_type'] == 'bullish' else "🔴"
            ob_zones_display.append(f"{zone_type} {zone['bottom']:.2f}-{zone['top']:.2f}")
    
    result_data = {
        "price": last_row['Close'],
        "trend": trend,
        "rsi": round(last_row['RSI'], 2),
        "signal": final_signal,
        "smc": smc_text,
        "price_action": pa_text,
        "chart_patterns": "Disabled",
        "sr_zones": sr_display,
        "fvg_zones": " | ".join(fvg_zones_display) if fvg_zones_display else "None",
        "ob_zones": " | ".join(ob_zones_display) if ob_zones_display else "None"
    }
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "data": result_data,
        "global_trend": global_trend
    }
