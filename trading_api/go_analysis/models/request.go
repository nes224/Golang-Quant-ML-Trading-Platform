package models

// OHLC represents a single candlestick
type OHLC struct {
	Open  float64 `json:"open"`
	High  float64 `json:"high"`
	Low   float64 `json:"low"`
	Close float64 `json:"close"`
}

// IndicatorRequest represents request for indicator calculation
type IndicatorRequest struct {
	Prices []float64 `json:"prices"`
	High   []float64 `json:"high"`
	Low    []float64 `json:"low"`
	Close  []float64 `json:"close"`
}

// PatternRequest represents request for pattern detection
type PatternRequest struct {
	OHLC []OHLC `json:"ohlc"`
}

// SMCRequest represents request for SMC analysis
type SMCRequest struct {
	OHLC []OHLC `json:"ohlc"`
}
