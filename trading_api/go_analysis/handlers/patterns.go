package handlers

import (
	"go_analysis/models"
	"math"
	"net/http"

	"github.com/gin-gonic/gin"
)

// DetectPatterns handles POST /detect/patterns
func DetectPatterns(c *gin.Context) {
	var req models.PatternRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ohlc := req.OHLC
	response := models.PatternResponse{
		Hammer:           make([]bool, len(ohlc)),
		InvertedHammer:   make([]bool, len(ohlc)),
		HangingMan:       make([]bool, len(ohlc)),
		DragonflyDoji:    make([]bool, len(ohlc)),
		GravestoneDoji:   make([]bool, len(ohlc)),
		BullishEngulfing: make([]bool, len(ohlc)),
		BearishEngulfing: make([]bool, len(ohlc)),
	}

	for i := 1; i < len(ohlc); i++ {
		candle := ohlc[i]
		body := math.Abs(candle.Close - candle.Open)
		totalRange := candle.High - candle.Low
		upperShadow := candle.High - math.Max(candle.Open, candle.Close)
		lowerShadow := math.Min(candle.Open, candle.Close) - candle.Low

		// Hammer: small body at top, long lower shadow
		if body < totalRange*0.3 && lowerShadow > body*2 && upperShadow < body*0.5 {
			response.Hammer[i] = true
		}

		// Inverted Hammer: small body at bottom, long upper shadow
		if body < totalRange*0.3 && upperShadow > body*2 && lowerShadow < body*0.5 {
			response.InvertedHammer[i] = true
		}

		// Hanging Man: same as hammer but in uptrend
		if body < totalRange*0.3 && lowerShadow > body*2 && upperShadow < body*0.5 {
			response.HangingMan[i] = true
		}

		// Dragonfly Doji: open/close at high, long lower shadow
		if body < totalRange*0.1 && lowerShadow > totalRange*0.6 {
			response.DragonflyDoji[i] = true
		}

		// Gravestone Doji: open/close at low, long upper shadow
		if body < totalRange*0.1 && upperShadow > totalRange*0.6 {
			response.GravestoneDoji[i] = true
		}

		// Bullish Engulfing
		if i > 0 {
			prev := ohlc[i-1]
			if prev.Close < prev.Open && candle.Close > candle.Open &&
				candle.Open < prev.Close && candle.Close > prev.Open {
				response.BullishEngulfing[i] = true
			}

			// Bearish Engulfing
			if prev.Close > prev.Open && candle.Close < candle.Open &&
				candle.Open > prev.Close && candle.Close < prev.Open {
				response.BearishEngulfing[i] = true
			}
		}
	}

	c.JSON(http.StatusOK, response)
}
