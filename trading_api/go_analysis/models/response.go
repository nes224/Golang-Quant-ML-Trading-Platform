package models

// IndicatorResponse represents response for indicator calculation
type IndicatorResponse struct {
	EMA50  []float64 `json:"ema_50"`
	EMA200 []float64 `json:"ema_200"`
	RSI    []float64 `json:"rsi"`
	ATR    []float64 `json:"atr"`
}

// PatternResponse represents response for pattern detection
type PatternResponse struct {
	Hammer          []bool `json:"hammer"`
	InvertedHammer  []bool `json:"inverted_hammer"`
	HangingMan      []bool `json:"hanging_man"`
	DragonflyDoji   []bool `json:"dragonfly_doji"`
	GravestoneDoji  []bool `json:"gravestone_doji"`
	BullishEngulfing []bool `json:"bullish_engulfing"`
	BearishEngulfing []bool `json:"bearish_engulfing"`
}

// Zone represents a price zone (FVG, OB, S/R)
type Zone struct {
	ZoneType string  `json:"zone_type"` // "bullish" or "bearish"
	Top      float64 `json:"top"`
	Bottom   float64 `json:"bottom"`
	Index    int     `json:"index"`
	GapSize  float64 `json:"gap_size,omitempty"`
	Strength int     `json:"strength,omitempty"`
	Level    float64 `json:"level,omitempty"`
	Distance float64 `json:"distance,omitempty"`
}

// SMCResponse represents response for SMC analysis
type SMCResponse struct {
	SwingHighs   []bool    `json:"swing_highs"`
	SwingLows    []bool    `json:"swing_lows"`
	FVGBullish   []bool    `json:"fvg_bullish"`
	FVGBearish   []bool    `json:"fvg_bearish"`
	OBBullish    []bool    `json:"ob_bullish"`
	OBBearish    []bool    `json:"ob_bearish"`
	FVGZones     []Zone    `json:"fvg_zones"`
	OBZones      []Zone    `json:"ob_zones"`
	SRZones      []Zone    `json:"sr_zones"`
}
