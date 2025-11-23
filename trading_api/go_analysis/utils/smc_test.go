package utils

import (
	"go_analysis/models"
	"testing"
)

func TestDetectLiquiditySweeps(t *testing.T) {
	// Create test data with a bullish sweep
	// Pattern: Low at index 5, then price breaks below and closes above
	ohlc := []models.OHLC{
		{Open: 100, High: 105, Low: 95, Close: 100},  // 0
		{Open: 100, High: 104, Low: 96, Close: 102},  // 1
		{Open: 102, High: 106, Low: 98, Close: 104},  // 2
		{Open: 104, High: 108, Low: 100, Close: 106}, // 3
		{Open: 106, High: 110, Low: 102, Close: 108}, // 4
		{Open: 108, High: 112, Low: 104, Close: 105}, // 5 - Swing Low at 104
		{Open: 105, High: 109, Low: 101, Close: 107}, // 6
		{Open: 107, High: 111, Low: 103, Close: 109}, // 7
		{Open: 109, High: 113, Low: 102, Close: 108}, // 8 - Sweep: Low 102 < 104, Close 108 > 104
		{Open: 108, High: 112, Low: 104, Close: 110}, // 9
	}

	// Mark swing points (simplified - just mark index 5 as swing low)
	swingHighs := make([]bool, len(ohlc))
	swingLows := make([]bool, len(ohlc))
	swingLows[5] = true // Swing low at index 5

	sweeps := DetectLiquiditySweeps(ohlc, swingHighs, swingLows)

	if len(sweeps) == 0 {
		t.Error("Expected to detect at least one sweep, got none")
	}

	if len(sweeps) > 0 {
		sweep := sweeps[0]
		if sweep.Type != "bullish" {
			t.Errorf("Expected bullish sweep, got %s", sweep.Type)
		}
		if sweep.SweptLevel != 104.0 {
			t.Errorf("Expected swept level 104.0, got %f", sweep.SweptLevel)
		}
		if sweep.Index != 8 {
			t.Errorf("Expected sweep at index 8, got %d", sweep.Index)
		}
		t.Logf("✅ Detected sweep: %+v", sweep)
	}
}

func TestDetectLiquiditySweeps_NoSweeps(t *testing.T) {
	// Test with data that has no sweeps
	ohlc := []models.OHLC{
		{Open: 100, High: 105, Low: 95, Close: 100},
		{Open: 100, High: 104, Low: 96, Close: 102},
		{Open: 102, High: 106, Low: 98, Close: 104},
	}

	swingHighs := make([]bool, len(ohlc))
	swingLows := make([]bool, len(ohlc))

	sweeps := DetectLiquiditySweeps(ohlc, swingHighs, swingLows)

	if len(sweeps) != 0 {
		t.Errorf("Expected no sweeps, got %d", len(sweeps))
	}
}

func TestDetectLiquiditySweeps_EmptyData(t *testing.T) {
	// Test with empty data
	ohlc := []models.OHLC{}
	swingHighs := []bool{}
	swingLows := []bool{}

	sweeps := DetectLiquiditySweeps(ohlc, swingHighs, swingLows)

	if len(sweeps) != 0 {
		t.Errorf("Expected no sweeps for empty data, got %d", len(sweeps))
	}
}
