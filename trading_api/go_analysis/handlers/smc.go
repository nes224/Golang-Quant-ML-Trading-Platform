package handlers

import (
	"go_analysis/models"
	"go_analysis/utils"
	"net/http"

	"github.com/gin-gonic/gin"
)

// AnalyzeSMC handles POST /analyze/smc
func AnalyzeSMC(c *gin.Context) {
	var req models.SMCRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ohlc := req.OHLC

	// Use goroutines for parallel SMC analysis
	type smcResult struct {
		swingHighs   []bool
		swingLows    []bool
		fvgBullish   []bool
		fvgBearish   []bool
		fvgZones     []models.Zone
		obBullish    []bool
		obBearish    []bool
		obZones      []models.Zone
		srZones      []models.Zone
	}

	resultChan := make(chan smcResult, 1)

	go func() {
		var r smcResult
		done := make(chan bool, 4)

		// Swing points (needed for S/R zones)
		go func() {
			r.swingHighs, r.swingLows = utils.IdentifySwingPoints(ohlc, 5, 5)
			done <- true
		}()

		// FVG analysis
		go func() {
			r.fvgBullish, r.fvgBearish, r.fvgZones = utils.IdentifyFVG(ohlc)
			done <- true
		}()

		// Order Blocks analysis
		go func() {
			r.obBullish, r.obBearish, r.obZones = utils.IdentifyOrderBlocks(ohlc)
			done <- true
		}()

		// Wait for swing points before calculating S/R zones
		<-done // Wait for swing points

		// S/R Zones (depends on swing points)
		go func() {
			r.srZones = utils.IdentifySRZones(ohlc, r.swingHighs, r.swingLows)
			done <- true
		}()

		// Wait for remaining goroutines
		for i := 0; i < 3; i++ {
			<-done
		}

		resultChan <- r
	}()

	// Get result from channel
	r := <-resultChan

	response := models.SMCResponse{
		SwingHighs:   r.swingHighs,
		SwingLows:    r.swingLows,
		FVGBullish:   r.fvgBullish,
		FVGBearish:   r.fvgBearish,
		OBBullish:    r.obBullish,
		OBBearish:    r.obBearish,
		FVGZones:     r.fvgZones,
		OBZones:      r.obZones,
		SRZones:      r.srZones,
	}

	c.JSON(http.StatusOK, response)
}
