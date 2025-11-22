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

	// Identify swing points
	swingHighs, swingLows := utils.IdentifySwingPoints(ohlc, 5, 5)

	// Identify FVG
	fvgBullish, fvgBearish, fvgZones := utils.IdentifyFVG(ohlc)

	// Identify Order Blocks
	obBullish, obBearish, obZones := utils.IdentifyOrderBlocks(ohlc)

	// Identify S/R Zones
	srZones := utils.IdentifySRZones(ohlc, swingHighs, swingLows)

	response := models.SMCResponse{
		SwingHighs:   swingHighs,
		SwingLows:    swingLows,
		FVGBullish:   fvgBullish,
		FVGBearish:   fvgBearish,
		OBBullish:    obBullish,
		OBBearish:    obBearish,
		FVGZones:     fvgZones,
		OBZones:      obZones,
		SRZones:      srZones,
	}

	c.JSON(http.StatusOK, response)
}
