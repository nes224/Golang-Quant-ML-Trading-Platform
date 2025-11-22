use crate::OHLC;
use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct FvgZone {
    pub zone_type: String,  // "bullish" or "bearish"
    pub top: f64,
    pub bottom: f64,
    pub index: usize,
    pub gap_size: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct OrderBlockZone {
    pub zone_type: String,  // "bullish" or "bearish"
    pub top: f64,
    pub bottom: f64,
    pub index: usize,
}

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

/// Detect Fair Value Gaps (FVG) as Zones
pub fn detect_fvg_zones(ohlc: &[OHLC]) -> Vec<FvgZone> {
    let len = ohlc.len();
    let mut zones = Vec::new();
    
    if len < 3 {
        return zones;
    }
    
    for i in 2..len {
        // Bullish FVG: Low[i] > High[i-2] (gap between candles)
        if ohlc[i].low > ohlc[i-2].high && ohlc[i].close > ohlc[i].open {
            let gap_size = ohlc[i].low - ohlc[i-2].high;
            zones.push(FvgZone {
                zone_type: "bullish".to_string(),
                top: ohlc[i].low,
                bottom: ohlc[i-2].high,
                index: i,
                gap_size,
            });
        }
        
        // Bearish FVG: High[i] < Low[i-2] (gap between candles)
        if ohlc[i].high < ohlc[i-2].low && ohlc[i].close < ohlc[i].open {
            let gap_size = ohlc[i-2].low - ohlc[i].high;
            zones.push(FvgZone {
                zone_type: "bearish".to_string(),
                top: ohlc[i-2].low,
                bottom: ohlc[i].high,
                index: i,
                gap_size,
            });
        }
    }
    
    zones
}

/// Detect Order Blocks as Zones
pub fn detect_order_block_zones(ohlc: &[OHLC]) -> Vec<OrderBlockZone> {
    let len = ohlc.len();
    let mut zones = Vec::new();
    
    if len < 2 {
        return zones;
    }
    
    for i in 1..len {
        let prev_is_red = ohlc[i-1].open > ohlc[i-1].close;
        let curr_is_green = ohlc[i].close > ohlc[i].open;
        let bullish_engulf = ohlc[i].close > ohlc[i-1].open;
        
        // Bullish Order Block: Last red candle before bullish engulfing
        if prev_is_red && curr_is_green && bullish_engulf {
            zones.push(OrderBlockZone {
                zone_type: "bullish".to_string(),
                top: ohlc[i-1].open,      // Top of the red candle
                bottom: ohlc[i-1].close,  // Bottom of the red candle
                index: i-1,
            });
        }
        
        let prev_is_green = ohlc[i-1].close > ohlc[i-1].open;
        let curr_is_red = ohlc[i].open > ohlc[i].close;
        let bearish_engulf = ohlc[i].close < ohlc[i-1].open;
        
        // Bearish Order Block: Last green candle before bearish engulfing
        if prev_is_green && curr_is_red && bearish_engulf {
            zones.push(OrderBlockZone {
                zone_type: "bearish".to_string(),
                top: ohlc[i-1].close,    // Top of the green candle
                bottom: ohlc[i-1].open,  // Bottom of the green candle
                index: i-1,
            });
        }
    }
    
    zones
}

/// Legacy function for backward compatibility (returns booleans)
pub fn detect_fvg(ohlc: &[OHLC]) -> (Vec<bool>, Vec<bool>) {
    let zones = detect_fvg_zones(ohlc);
    let len = ohlc.len();
    let mut bullish_fvg = vec![false; len];
    let mut bearish_fvg = vec![false; len];
    
    for zone in zones {
        if zone.zone_type == "bullish" {
            bullish_fvg[zone.index] = true;
        } else {
            bearish_fvg[zone.index] = true;
        }
    }
    
    (bullish_fvg, bearish_fvg)
}

/// Legacy function for backward compatibility (returns booleans)
pub fn detect_order_blocks(ohlc: &[OHLC]) -> (Vec<bool>, Vec<bool>) {
    let zones = detect_order_block_zones(ohlc);
    let len = ohlc.len();
    let mut bullish_ob = vec![false; len];
    let mut bearish_ob = vec![false; len];
    
    for zone in zones {
        if zone.zone_type == "bullish" {
            bullish_ob[zone.index] = true;
        } else {
            bearish_ob[zone.index] = true;
        }
    }
    
    (bullish_ob, bearish_ob)
}

/// Detect Liquidity Sweeps (Stop Hunts)
pub fn detect_liquidity_sweep(
    high: &[f64],
    low: &[f64],
    close: &[f64],
    lookback: usize
) -> (Vec<bool>, Vec<bool>) {
    let len = high.len();
    let mut bullish_sweep = vec![false; len];
    let mut bearish_sweep = vec![false; len];
    
    if len < lookback + 2 {
        return (bullish_sweep, bearish_sweep);
    }
    
    for i in lookback..len {
        // Find recent low and high in lookback period
        let start_idx = i.saturating_sub(lookback);
        let recent_low = low[start_idx..i].iter().cloned().fold(f64::INFINITY, f64::min);
        let recent_high = high[start_idx..i].iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        
        // Bullish Sweep: Price breaks below recent low, then closes back above it
        if low[i] < recent_low && close[i] > recent_low {
            bullish_sweep[i] = true;
        }
        
        // Bearish Sweep: Price breaks above recent high, then closes back below it
        if high[i] > recent_high && close[i] < recent_high {
            bearish_sweep[i] = true;
        }
    }
    
    (bullish_sweep, bearish_sweep)
}
