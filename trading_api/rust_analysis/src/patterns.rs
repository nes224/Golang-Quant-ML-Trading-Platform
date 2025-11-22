use crate::OHLC;

/// Detect Hammer pattern
pub fn detect_hammer(ohlc: &[OHLC]) -> Vec<bool> {
    let len = ohlc.len();
    let mut result = vec![false; len];
    
    for i in 0..len {
        let body = (ohlc[i].close - ohlc[i].open).abs();
        let upper_wick = ohlc[i].high - ohlc[i].close.max(ohlc[i].open);
        let lower_wick = ohlc[i].close.min(ohlc[i].open) - ohlc[i].low;
        let total_range = ohlc[i].high - ohlc[i].low;
        
        if total_range > 0.0 {
            // Hammer: small body, long lower wick, small upper wick
            if lower_wick > body * 2.0 && upper_wick < body * 0.5 {
                result[i] = true;
            }
        }
    }
    
    result
}

/// Detect Inverted Hammer pattern
pub fn detect_inverted_hammer(ohlc: &[OHLC]) -> Vec<bool> {
    let len = ohlc.len();
    let mut result = vec![false; len];
    
    for i in 0..len {
        let body = (ohlc[i].close - ohlc[i].open).abs();
        let upper_wick = ohlc[i].high - ohlc[i].close.max(ohlc[i].open);
        let lower_wick = ohlc[i].close.min(ohlc[i].open) - ohlc[i].low;
        let total_range = ohlc[i].high - ohlc[i].low;
        
        if total_range > 0.0 {
            // Inverted Hammer: small body, long upper wick, small lower wick
            if upper_wick > body * 2.0 && lower_wick < body * 0.5 {
                result[i] = true;
            }
        }
    }
    
    result
}

/// Detect Hanging Man pattern
pub fn detect_hanging_man(ohlc: &[OHLC]) -> Vec<bool> {
    // Hanging Man is same shape as Hammer but appears in uptrend
    // For now, use same logic as Hammer
    detect_hammer(ohlc)
}

/// Detect Bullish Engulfing pattern
pub fn detect_bullish_engulfing(ohlc: &[OHLC]) -> Vec<bool> {
    let len = ohlc.len();
    let mut result = vec![false; len];
    
    for i in 1..len {
        let prev_bearish = ohlc[i-1].close < ohlc[i-1].open;
        let curr_bullish = ohlc[i].close > ohlc[i].open;
        
        if prev_bearish && curr_bullish {
            // Current candle engulfs previous
            if ohlc[i].open < ohlc[i-1].close && ohlc[i].close > ohlc[i-1].open {
                result[i] = true;
            }
        }
    }
    
    result
}

/// Detect Bearish Engulfing pattern
pub fn detect_bearish_engulfing(ohlc: &[OHLC]) -> Vec<bool> {
    let len = ohlc.len();
    let mut result = vec![false; len];
    
    for i in 1..len {
        let prev_bullish = ohlc[i-1].close > ohlc[i-1].open;
        let curr_bearish = ohlc[i].close < ohlc[i].open;
        
        if prev_bullish && curr_bearish {
            // Current candle engulfs previous
            if ohlc[i].open > ohlc[i-1].close && ohlc[i].close < ohlc[i-1].open {
                result[i] = true;
            }
        }
    }
    
    result
}
