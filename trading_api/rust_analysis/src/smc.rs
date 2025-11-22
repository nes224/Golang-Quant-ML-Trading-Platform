use crate::OHLC;



/// Identify Swing Highs and Swing Lows
pub fn identify_swing_points(high: &[f64], low: &[f64], pivot_legs: usize) -> (Vec<Option<f64>>, Vec<Option<f64>>) {
    let len = high.len();
    let window = pivot_legs * 2 + 1;
    
    let mut swing_highs = vec![None; len];
    let mut swing_lows = vec![None; len];
    
    if len < window {
        return (swing_highs, swing_lows);
    }
    
    for i in pivot_legs..(len - pivot_legs) {
        // Check if this is a swing high
        let mut is_swing_high = true;
        for j in (i - pivot_legs)..=(i + pivot_legs) {
            if j != i && high[j] >= high[i] {
                is_swing_high = false;
                break;
            }
        }
        if is_swing_high {
            swing_highs[i] = Some(high[i]);
        }
        
        // Check if this is a swing low
        let mut is_swing_low = true;
        for j in (i - pivot_legs)..=(i + pivot_legs) {
            if j != i && low[j] <= low[i] {
                is_swing_low = false;
                break;
            }
        }
        if is_swing_low {
            swing_lows[i] = Some(low[i]);
        }
    }
    
    (swing_highs, swing_lows)
}

/// Detect Fair Value Gaps (FVG)
pub fn detect_fvg(ohlc: &[OHLC]) -> (Vec<bool>, Vec<bool>) {
    let len = ohlc.len();
    let mut bullish_fvg = vec![false; len];
    let mut bearish_fvg = vec![false; len];
    
    if len < 3 {
        return (bullish_fvg, bearish_fvg);
    }
    
    for i in 2..len {
        // Bullish FVG: Low[i] > High[i-2]
        if ohlc[i].low > ohlc[i-2].high && ohlc[i].close > ohlc[i].open {
            bullish_fvg[i] = true;
        }
        
        // Bearish FVG: High[i] < Low[i-2]
        if ohlc[i].high < ohlc[i-2].low && ohlc[i].close < ohlc[i].open {
            bearish_fvg[i] = true;
        }
    }
    
    (bullish_fvg, bearish_fvg)
}

/// Detect Order Blocks
pub fn detect_order_blocks(ohlc: &[OHLC]) -> (Vec<bool>, Vec<bool>) {
    let len = ohlc.len();
    let mut bullish_ob = vec![false; len];
    let mut bearish_ob = vec![false; len];
    
    if len < 2 {
        return (bullish_ob, bearish_ob);
    }
    
    for i in 1..len {
        let prev_is_red = ohlc[i-1].open > ohlc[i-1].close;
        let curr_is_green = ohlc[i].close > ohlc[i].open;
        let bullish_engulf = ohlc[i].close > ohlc[i-1].open;
        
        if prev_is_red && curr_is_green && bullish_engulf {
            bullish_ob[i] = true;
        }
        
        let prev_is_green = ohlc[i-1].close > ohlc[i-1].open;
        let curr_is_red = ohlc[i].open > ohlc[i].close;
        let bearish_engulf = ohlc[i].close < ohlc[i-1].open;
        
        if prev_is_green && curr_is_red && bearish_engulf {
            bearish_ob[i] = true;
        }
    }
    
    (bullish_ob, bearish_ob)
}
