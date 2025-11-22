package utils

import (
	"math"
)

// CalculateEMA calculates Exponential Moving Average
func CalculateEMA(prices []float64, period int) []float64 {
	if len(prices) < period {
		return make([]float64, len(prices))
	}

	result := make([]float64, len(prices))
	multiplier := 2.0 / float64(period+1)

	// Calculate initial SMA
	sum := 0.0
	for i := 0; i < period; i++ {
		sum += prices[i]
	}
	result[period-1] = sum / float64(period)

	// Calculate EMA
	for i := period; i < len(prices); i++ {
		result[i] = (prices[i]-result[i-1])*multiplier + result[i-1]
	}

	return result
}

// CalculateRSI calculates Relative Strength Index
func CalculateRSI(prices []float64, period int) []float64 {
	if len(prices) < period+1 {
		return make([]float64, len(prices))
	}

	result := make([]float64, len(prices))
	gains := make([]float64, len(prices))
	losses := make([]float64, len(prices))

	// Calculate price changes
	for i := 1; i < len(prices); i++ {
		change := prices[i] - prices[i-1]
		if change > 0 {
			gains[i] = change
		} else {
			losses[i] = -change
		}
	}

	// Calculate initial average gain/loss
	avgGain := 0.0
	avgLoss := 0.0
	for i := 1; i <= period; i++ {
		avgGain += gains[i]
		avgLoss += losses[i]
	}
	avgGain /= float64(period)
	avgLoss /= float64(period)

	// Calculate RSI
	for i := period; i < len(prices); i++ {
		if i > period {
			avgGain = (avgGain*float64(period-1) + gains[i]) / float64(period)
			avgLoss = (avgLoss*float64(period-1) + losses[i]) / float64(period)
		}

		if avgLoss == 0 {
			result[i] = 100
		} else {
			rs := avgGain / avgLoss
			result[i] = 100 - (100 / (1 + rs))
		}
	}

	return result
}

// CalculateATR calculates Average True Range
func CalculateATR(high, low, close []float64, period int) []float64 {
	if len(high) < period+1 {
		return make([]float64, len(high))
	}

	result := make([]float64, len(high))
	trueRanges := make([]float64, len(high))

	// Calculate True Range
	for i := 1; i < len(high); i++ {
		highLow := high[i] - low[i]
		highClose := math.Abs(high[i] - close[i-1])
		lowClose := math.Abs(low[i] - close[i-1])

		trueRanges[i] = math.Max(highLow, math.Max(highClose, lowClose))
	}

	// Calculate initial ATR (SMA of TR)
	sum := 0.0
	for i := 1; i <= period; i++ {
		sum += trueRanges[i]
	}
	result[period] = sum / float64(period)

	// Calculate ATR (EMA of TR)
	for i := period + 1; i < len(high); i++ {
		result[i] = (result[i-1]*float64(period-1) + trueRanges[i]) / float64(period)
	}

	return result
}
