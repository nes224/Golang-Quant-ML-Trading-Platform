package handlers

import (
	"go_analysis/models"
	"go_analysis/utils"
	"net/http"

	"github.com/gin-gonic/gin"
)

// CalculateIndicators handles POST /calculate/indicators
func CalculateIndicators(c *gin.Context) {
	var req models.IndicatorRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Use goroutines for parallel calculation
	type result struct {
		ema50  []float64
		ema200 []float64
		rsi    []float64
		atr    []float64
	}

	resultChan := make(chan result, 1)

	go func() {
		var r result
		// Calculate all indicators concurrently using goroutines
		done := make(chan bool, 4)

		go func() {
			r.ema50 = utils.CalculateEMA(req.Close, 50)
			done <- true
		}()

		go func() {
			r.ema200 = utils.CalculateEMA(req.Close, 200)
			done <- true
		}()

		go func() {
			r.rsi = utils.CalculateRSI(req.Close, 14)
			done <- true
		}()

		go func() {
			r.atr = utils.CalculateATR(req.High, req.Low, req.Close, 14)
			done <- true
		}()

		// Wait for all goroutines to complete
		for i := 0; i < 4; i++ {
			<-done
		}

		resultChan <- r
	}()

	// Get result from channel
	r := <-resultChan

	response := models.IndicatorResponse{
		EMA50:  r.ema50,
		EMA200: r.ema200,
		RSI:    r.rsi,
		ATR:    r.atr,
	}

	c.JSON(http.StatusOK, response)
}
