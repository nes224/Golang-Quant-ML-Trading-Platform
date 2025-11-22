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

	// Calculate indicators
	ema50 := utils.CalculateEMA(req.Close, 50)
	ema200 := utils.CalculateEMA(req.Close, 200)
	rsi := utils.CalculateRSI(req.Close, 14)
	atr := utils.CalculateATR(req.High, req.Low, req.Close, 14)

	response := models.IndicatorResponse{
		EMA50:  ema50,
		EMA200: ema200,
		RSI:    rsi,
		ATR:    atr,
	}

	c.JSON(http.StatusOK, response)
}
