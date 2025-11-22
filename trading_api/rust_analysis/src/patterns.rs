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

/// Detect Dragonfly Doji
pub fn detect_dragonfly_doji(ohlc: &[OHLC]) -> Vec<bool> {
    let len = ohlc.len();
    let mut result = vec![false; len];
    
    for i in 0..len {
        let body = (ohlc[i].close - ohlc[i].open).abs();
        let upper_wick = ohlc[i].high - ohlc[i].close.max(ohlc[i].open);
        let lower_wick = ohlc[i].close.min(ohlc[i].open) - ohlc[i].low;
        let total_range = ohlc[i].high - ohlc[i].low;
        
        if total_range > 0.0 {
            // Dragonfly: tiny body, long lower wick, no upper wick
            if body < 0.05 * total_range && lower_wick > 0.7 * total_range && upper_wick < 0.05 * total_range {
                result[i] = true;
            }
        }
    }
    result
}

/// Detect Gravestone Doji
pub fn detect_gravestone_doji(ohlc: &[OHLC]) -> Vec<bool> {
    let len = ohlc.len();
    let mut result = vec![false; len];
    
    for i in 0..len {
        let body = (ohlc[i].close - ohlc[i].open).abs();
        let upper_wick = ohlc[i].high - ohlc[i].close.max(ohlc[i].open);
        let lower_wick = ohlc[i].close.min(ohlc[i].open) - ohlc[i].low;
        let total_range = ohlc[i].high - ohlc[i].low;
        
        if total_range > 0.0 {
            // Gravestone: tiny body, long upper wick, no lower wick
            if body < 0.05 * total_range && upper_wick > 0.7 * total_range && lower_wick < 0.05 * total_range {
                result[i] = true;
            }
        }
    }
    result
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

/// Detect Morning Star
pub fn detect_morning_star(ohlc: &[OHLC]) -> Vec<bool> {
    let len = ohlc.len();
    let mut result = vec![false; len];
    
    for i in 2..len {
        // Day 1: Bearish
        let day1_bearish = ohlc[i-2].close < ohlc[i-2].open;
        
        // Day 2: Small body (gap down ideally)
        let day2_body = (ohlc[i-1].close - ohlc[i-1].open).abs();
        let day2_range = ohlc[i-1].high - ohlc[i-1].low;
        let day2_small = day2_body < 0.3 * day2_range;
        
        // Day 3: Bullish, closes above midpoint of Day 1
        let day3_bullish = ohlc[i].close > ohlc[i].open;
        let day1_midpoint = (ohlc[i-2].open + ohlc[i-2].close) / 2.0;
        let day3_closes_high = ohlc[i].close > day1_midpoint;
        
        if day1_bearish && day2_small && day3_bullish && day3_closes_high {
            result[i] = true;
        }
    }
    result
}

/// Detect Evening Star
pub fn detect_evening_star(ohlc: &[OHLC]) -> Vec<bool> {
    let len = ohlc.len();
    let mut result = vec![false; len];
    
    for i in 2..len {
        // Day 1: Bullish
        let day1_bullish = ohlc[i-2].close > ohlc[i-2].open;
        
        // Day 2: Small body
        let day2_body = (ohlc[i-1].close - ohlc[i-1].open).abs();
        let day2_range = ohlc[i-1].high - ohlc[i-1].low;
        let day2_small = day2_body < 0.3 * day2_range;
        
        // Day 3: Bearish, closes below midpoint of Day 1
        let day3_bearish = ohlc[i].close < ohlc[i].open;
        let day1_midpoint = (ohlc[i-2].open + ohlc[i-2].close) / 2.0;
        let day3_closes_low = ohlc[i].close < day1_midpoint;
        
        if day1_bullish && day2_small && day3_bearish && day3_closes_low {
            result[i] = true;
        }
    }
    result
}
