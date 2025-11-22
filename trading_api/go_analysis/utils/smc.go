package utils

import (
	"go_analysis/models"
	"math"
)

// IdentifySwingPoints identifies swing highs and lows
func IdentifySwingPoints(ohlc []models.OHLC, leftBars, rightBars int) ([]bool, []bool) {
	swingHighs := make([]bool, len(ohlc))
	swingLows := make([]bool, len(ohlc))

	for i := leftBars; i < len(ohlc)-rightBars; i++ {
		isSwingHigh := true
		isSwingLow := true

		// Check left side
		for j := 1; j <= leftBars; j++ {
			if ohlc[i].High <= ohlc[i-j].High {
				isSwingHigh = false
			}
			if ohlc[i].Low >= ohlc[i-j].Low {
				isSwingLow = false
			}
		}

		// Check right side
		for j := 1; j <= rightBars; j++ {
			if ohlc[i].High <= ohlc[i+j].High {
				isSwingHigh = false
			}
			if ohlc[i].Low >= ohlc[i+j].Low {
				isSwingLow = false
			}
		}

		swingHighs[i] = isSwingHigh
		swingLows[i] = isSwingLow
	}

	return swingHighs, swingLows
}

// IdentifyFVG identifies Fair Value Gaps
func IdentifyFVG(ohlc []models.OHLC) ([]bool, []bool, []models.Zone) {
	fvgBullish := make([]bool, len(ohlc))
	fvgBearish := make([]bool, len(ohlc))
	zones := []models.Zone{}

	for i := 2; i < len(ohlc); i++ {
		// Bullish FVG: current low > high 2 candles ago
		if ohlc[i].Low > ohlc[i-2].High && ohlc[i].Close > ohlc[i].Open {
			fvgBullish[i] = true
			zones = append(zones, models.Zone{
				ZoneType: "bullish",
				Bottom:   ohlc[i-2].High,
				Top:      ohlc[i].Low,
				Index:    i,
				GapSize:  ohlc[i].Low - ohlc[i-2].High,
			})
		}

		// Bearish FVG: current high < low 2 candles ago
		if ohlc[i].High < ohlc[i-2].Low && ohlc[i].Close < ohlc[i].Open {
			fvgBearish[i] = true
			zones = append(zones, models.Zone{
				ZoneType: "bearish",
				Bottom:   ohlc[i].High,
				Top:      ohlc[i-2].Low,
				Index:    i,
				GapSize:  ohlc[i-2].Low - ohlc[i].High,
			})
		}
	}

	return fvgBullish, fvgBearish, zones
}

// IdentifyOrderBlocks identifies Order Blocks
func IdentifyOrderBlocks(ohlc []models.OHLC) ([]bool, []bool, []models.Zone) {
	obBullish := make([]bool, len(ohlc))
	obBearish := make([]bool, len(ohlc))
	zones := []models.Zone{}

	for i := 1; i < len(ohlc); i++ {
		// Bullish OB: down candle followed by strong up move
		if ohlc[i-1].Close < ohlc[i-1].Open && ohlc[i].Close > ohlc[i].Open {
			bodySize := ohlc[i].Close - ohlc[i].Open
			prevBodySize := ohlc[i-1].Open - ohlc[i-1].Close
			if bodySize > prevBodySize*1.5 {
				obBullish[i-1] = true
				zones = append(zones, models.Zone{
					ZoneType: "bullish",
					Bottom:   ohlc[i-1].Low,
					Top:      ohlc[i-1].High,
					Index:    i - 1,
				})
			}
		}

		// Bearish OB: up candle followed by strong down move
		if ohlc[i-1].Close > ohlc[i-1].Open && ohlc[i].Close < ohlc[i].Open {
			bodySize := ohlc[i].Open - ohlc[i].Close
			prevBodySize := ohlc[i-1].Close - ohlc[i-1].Open
			if bodySize > prevBodySize*1.5 {
				obBearish[i-1] = true
				zones = append(zones, models.Zone{
					ZoneType: "bearish",
					Bottom:   ohlc[i-1].Low,
					Top:      ohlc[i-1].High,
					Index:    i - 1,
				})
			}
		}
	}

	return obBullish, obBearish, zones
}

// IdentifySRZones identifies Support and Resistance zones
func IdentifySRZones(ohlc []models.OHLC, swingHighs, swingLows []bool) []models.Zone {
	zones := []models.Zone{}
	threshold := 0.002 // 0.2% clustering threshold

	// Get current price for distance calculation
	currentPrice := ohlc[len(ohlc)-1].Close

	// Collect swing high levels
	highLevels := []struct {
		price float64
		index int
	}{}
	for i, isHigh := range swingHighs {
		if isHigh {
			highLevels = append(highLevels, struct {
				price float64
				index int
			}{ohlc[i].High, i})
		}
	}

	// Collect swing low levels
	lowLevels := []struct {
		price float64
		index int
	}{}
	for i, isLow := range swingLows {
		if isLow {
			lowLevels = append(lowLevels, struct {
				price float64
				index int
			}{ohlc[i].Low, i})
		}
	}

	// Cluster resistance levels
	for _, level := range highLevels {
		// Count nearby levels
		strength := 1
		for _, other := range highLevels {
			if other.index != level.index {
				diff := math.Abs(level.price-other.price) / level.price
				if diff < threshold {
					strength++
				}
			}
		}

		if strength >= 2 {
			zones = append(zones, models.Zone{
				ZoneType: "resistance",
				Level:    level.price,
				Bottom:   level.price * (1 - threshold),
				Top:      level.price * (1 + threshold),
				Strength: strength,
				Distance: math.Abs(currentPrice - level.price),
			})
		}
	}

	// Cluster support levels
	for _, level := range lowLevels {
		// Count nearby levels
		strength := 1
		for _, other := range lowLevels {
			if other.index != level.index {
				diff := math.Abs(level.price-other.price) / level.price
				if diff < threshold {
					strength++
				}
			}
		}

		if strength >= 2 {
			zones = append(zones, models.Zone{
				ZoneType: "support",
				Level:    level.price,
				Bottom:   level.price * (1 - threshold),
				Top:      level.price * (1 + threshold),
				Strength: strength,
				Distance: math.Abs(currentPrice - level.price),
			})
		}
	}

	return zones
}
