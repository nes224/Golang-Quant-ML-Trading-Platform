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

// IdentifySRZones identifies Support and Resistance zones based on Rejection and Momentum
func IdentifySRZones(ohlc []models.OHLC, swingHighs, swingLows []bool) []models.Zone {
	zones := []models.Zone{}
	threshold := 0.0005   // 0.05% clustering threshold (tighter)
	maxZoneWidth := 0.002 // 0.2% max width allowed for a single zone
	minTouches := 1

	if len(ohlc) < 20 {
		return zones
	}

	currentPrice := ohlc[len(ohlc)-1].Close

	type PotentialLevel struct {
		Price       float64
		Type        string
		IsRejection bool
		Index       int
	}

	potentialLevels := []PotentialLevel{}

	// Helper to check momentum
	checkMomentum := func(idx int, isBullish bool, swingPrice float64) bool {
		// Check next 3 bars
		for k := 1; k <= 3; k++ {
			if idx+k >= len(ohlc) {
				break
			}
			futureClose := ohlc[idx+k].Close
			if isBullish {
				if futureClose > ohlc[idx].High { // Price moved up past the high of the swing candle
					return true
				}
			} else {
				if futureClose < ohlc[idx].Low { // Price moved down past the low of the swing candle
					return true
				}
			}
		}
		return false
	}

	// Analyze Swing Lows (Support Candidates)
	for i, isLow := range swingLows {
		if isLow {
			c := ohlc[i]
			bodySize := math.Abs(c.Close - c.Open)
			lowerWick := math.Min(c.Open, c.Close) - c.Low
			totalRange := c.High - c.Low

			// Bullish Rejection
			isRejection := (lowerWick > bodySize) && (lowerWick > totalRange*0.3)

			// Check Momentum
			hasMomentum := checkMomentum(i, true, c.High)

			if isRejection || hasMomentum {
				potentialLevels = append(potentialLevels, PotentialLevel{
					Price:       c.Low,
					Type:        "support",
					IsRejection: isRejection,
					Index:       i,
				})
			}
		}
	}

	// Analyze Swing Highs (Resistance Candidates)
	for i, isHigh := range swingHighs {
		if isHigh {
			c := ohlc[i]
			bodySize := math.Abs(c.Close - c.Open)
			upperWick := c.High - math.Max(c.Open, c.Close)
			totalRange := c.High - c.Low

			// Bearish Rejection
			isRejection := (upperWick > bodySize) && (upperWick > totalRange*0.3)

			// Check Momentum
			hasMomentum := checkMomentum(i, false, c.Low)

			if isRejection || hasMomentum {
				potentialLevels = append(potentialLevels, PotentialLevel{
					Price:       c.High,
					Type:        "resistance",
					IsRejection: isRejection,
					Index:       i,
				})
			}
		}
	}

	// If no strict levels, fallback to raw swings
	if len(potentialLevels) == 0 {
		for i, isLow := range swingLows {
			if isLow {
				potentialLevels = append(potentialLevels, PotentialLevel{Price: ohlc[i].Low, Type: "support", Index: i})
			}
		}
		for i, isHigh := range swingHighs {
			if isHigh {
				potentialLevels = append(potentialLevels, PotentialLevel{Price: ohlc[i].High, Type: "resistance", Index: i})
			}
		}
	}

	// Sort by price for clustering
	for i := 0; i < len(potentialLevels); i++ {
		for j := i + 1; j < len(potentialLevels); j++ {
			if potentialLevels[i].Price > potentialLevels[j].Price {
				potentialLevels[i], potentialLevels[j] = potentialLevels[j], potentialLevels[i]
			}
		}
	}

	// Cluster Levels
	if len(potentialLevels) == 0 {
		return zones
	}

	currentCluster := []PotentialLevel{potentialLevels[0]}

	createZone := func(cluster []PotentialLevel) models.Zone {
		sumPrice := 0.0
		minPrice := cluster[0].Price
		maxPrice := cluster[0].Price
		hasRejection := false
		supCount := 0
		resCount := 0

		for _, p := range cluster {
			sumPrice += p.Price
			if p.Price < minPrice {
				minPrice = p.Price
			}
			if p.Price > maxPrice {
				maxPrice = p.Price
			}
			if p.IsRejection {
				hasRejection = true
			}
			if p.Type == "support" {
				supCount++
			} else {
				resCount++
			}
		}

		avgPrice := sumPrice / float64(len(cluster))

		zoneType := "support"
		if resCount > supCount {
			zoneType = "resistance"
		} else if supCount == resCount {
			if avgPrice > currentPrice {
				zoneType = "resistance"
			}
		}

		return models.Zone{
			ZoneType:     zoneType,
			Level:        avgPrice,
			Top:          maxPrice,
			Bottom:       minPrice,
			Strength:     len(cluster),
			Distance:     math.Abs(currentPrice - avgPrice),
			HasRejection: hasRejection,
		}
	}

	for i := 1; i < len(potentialLevels); i++ {
		item := potentialLevels[i]
		prevItem := currentCluster[len(currentCluster)-1]
		firstItem := currentCluster[0]

		diffPct := math.Abs(item.Price-prevItem.Price) / prevItem.Price
		totalWidthPct := math.Abs(item.Price-firstItem.Price) / firstItem.Price

		if diffPct <= threshold && totalWidthPct <= maxZoneWidth {
			currentCluster = append(currentCluster, item)
		} else {
			zones = append(zones, createZone(currentCluster))
			currentCluster = []PotentialLevel{item}
		}
	}
	if len(currentCluster) > 0 {
		zones = append(zones, createZone(currentCluster))
	}

	// Filter and Sort Zones
	filteredZones := []models.Zone{}
	for _, z := range zones {
		if z.HasRejection || z.Strength >= minTouches {
			filteredZones = append(filteredZones, z)
		}
	}
	zones = filteredZones

	// Sort by Strength (desc) then Distance (asc)
	for i := 0; i < len(zones); i++ {
		for j := i + 1; j < len(zones); j++ {
			// Primary: Strength (desc)
			if zones[j].Strength > zones[i].Strength {
				zones[i], zones[j] = zones[j], zones[i]
			} else if zones[j].Strength == zones[i].Strength {
				// Secondary: HasRejection (true > false)
				if zones[j].HasRejection && !zones[i].HasRejection {
					zones[i], zones[j] = zones[j], zones[i]
				} else if zones[j].HasRejection == zones[i].HasRejection {
					// Tertiary: Distance (asc)
					if zones[j].Distance < zones[i].Distance {
						zones[i], zones[j] = zones[j], zones[i]
					}
				}
			}
		}
	}

	// Top 5
	if len(zones) > 5 {
		zones = zones[:5]
	}

	// Final sort by distance for display
	for i := 0; i < len(zones); i++ {
		for j := i + 1; j < len(zones); j++ {
			if zones[j].Distance < zones[i].Distance {
				zones[i], zones[j] = zones[j], zones[i]
			}
		}
	}

	return zones
}

// DetectLiquiditySweeps identifies liquidity sweeps (stop hunts)
// Bullish Sweep: Price breaks below swing low, then closes back above it
// Bearish Sweep: Price breaks above swing high, then closes back below it
func DetectLiquiditySweeps(ohlc []models.OHLC, swingHighs, swingLows []bool) []models.LiquiditySweep {
	sweeps := []models.LiquiditySweep{}

	// Safety checks
	if len(ohlc) == 0 || len(swingHighs) == 0 || len(swingLows) == 0 {
		return sweeps
	}

	if len(ohlc) != len(swingHighs) || len(ohlc) != len(swingLows) {
		return sweeps
	}

	maxLookAhead := 3 // Check up to 3 candles for reversal

	// Detect sweeps at swing highs (bearish sweeps)
	for i := 0; i < len(ohlc)-maxLookAhead; i++ {
		if i >= len(swingHighs) || !swingHighs[i] {
			continue
		}

		swingLevel := ohlc[i].High

		// Check next 1-3 candles for sweep and reversal
		for j := 1; j <= maxLookAhead && i+j < len(ohlc); j++ {
			candle := ohlc[i+j]

			// Bearish sweep: High breaks above swing high, but Close is below it
			if candle.High > swingLevel && candle.Close < swingLevel {
				// Strength based on reversal speed (1 candle = strongest)
				strength := maxLookAhead - j + 1

				sweeps = append(sweeps, models.LiquiditySweep{
					Index:      i + j,
					Type:       "bearish",
					SweptLevel: swingLevel,
					Strength:   strength,
				})
				break // Found sweep, move to next swing point
			}
		}
	}

	// Detect sweeps at swing lows (bullish sweeps)
	for i := 0; i < len(ohlc)-maxLookAhead; i++ {
		if i >= len(swingLows) || !swingLows[i] {
			continue
		}

		swingLevel := ohlc[i].Low

		// Check next 1-3 candles for sweep and reversal
		for j := 1; j <= maxLookAhead && i+j < len(ohlc); j++ {
			candle := ohlc[i+j]

			// Bullish sweep: Low breaks below swing low, but Close is above it
			if candle.Low < swingLevel && candle.Close > swingLevel {
				// Strength based on reversal speed (1 candle = strongest)
				strength := maxLookAhead - j + 1

				sweeps = append(sweeps, models.LiquiditySweep{
					Index:      i + j,
					Type:       "bullish",
					SweptLevel: swingLevel,
					Strength:   strength,
				})
				break // Found sweep, move to next swing point
			}
		}
	}

	return sweeps
}
