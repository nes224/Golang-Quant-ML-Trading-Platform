/// Calculate Exponential Moving Average (EMA)
pub fn calculate_ema(prices: &[f64], period: usize) -> Vec<f64> {
    let len = prices.len();
    
    if len < period {
        return vec![0.0; len];
    }
    
    let mut ema = vec![0.0; len];
    let multiplier = 2.0 / (period as f64 + 1.0);
    
    // Initial SMA
    let sum: f64 = prices[..period].iter().sum();
    ema[period - 1] = sum / period as f64;
    
    // Calculate EMA
    for i in period..len {
        ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1];
    }
    
    ema
}

/// Calculate Relative Strength Index (RSI)
pub fn calculate_rsi(prices: &[f64], period: usize) -> Vec<f64> {
    let len = prices.len();
    
    if len < period + 1 {
        return vec![0.0; len];
    }
    
    let mut rsi = vec![0.0; len];
    let mut gains = vec![0.0; len];
    let mut losses = vec![0.0; len];
    
    // Calculate price changes
    for i in 1..len {
        let change = prices[i] - prices[i - 1];
        if change > 0.0 {
            gains[i] = change;
        } else {
            losses[i] = -change;
        }
    }
    
    // Initial average gain/loss
    let mut avg_gain: f64 = gains[1..=period].iter().sum::<f64>() / period as f64;
    let mut avg_loss: f64 = losses[1..=period].iter().sum::<f64>() / period as f64;
    
    // Calculate RSI using Wilder's smoothing
    let alpha = 1.0 / period as f64;
    
    for i in period..len {
        avg_gain = avg_gain * (1.0 - alpha) + gains[i] * alpha;
        avg_loss = avg_loss * (1.0 - alpha) + losses[i] * alpha;
        
        if avg_loss == 0.0 {
            rsi[i] = 100.0;
        } else {
            let rs = avg_gain / avg_loss;
            rsi[i] = 100.0 - (100.0 / (1.0 + rs));
        }
    }
    
    rsi
}

/// Calculate Average True Range (ATR)
pub fn calculate_atr(high: &[f64], low: &[f64], close: &[f64], period: usize) -> Vec<f64> {
    let len = high.len();
    
    if len < period + 1 {
        return vec![0.0; len];
    }
    
    let mut atr = vec![0.0; len];
    let mut true_ranges = vec![0.0; len];
    
    // Calculate True Range
    for i in 1..len {
        let hl = high[i] - low[i];
        let hc = (high[i] - close[i - 1]).abs();
        let lc = (low[i] - close[i - 1]).abs();
        true_ranges[i] = hl.max(hc).max(lc);
    }
    
    // Initial ATR (SMA of TR)
    let sum: f64 = true_ranges[1..=period].iter().sum();
    atr[period] = sum / period as f64;
    
    // Wilder's smoothing
    let alpha = 1.0 / period as f64;
    for i in (period + 1)..len {
        atr[i] = atr[i - 1] * (1.0 - alpha) + true_ranges[i] * alpha;
    }
    
    atr
}
