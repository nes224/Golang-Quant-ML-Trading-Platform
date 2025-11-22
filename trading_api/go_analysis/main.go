package main

import (
	"go_analysis/handlers"
	"log"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func main() {
	// Set Gin to release mode
	gin.SetMode(gin.ReleaseMode)

	// Create Gin router
	r := gin.Default()

	// Configure CORS
	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	config.AllowMethods = []string{"GET", "POST", "OPTIONS"}
	config.AllowHeaders = []string{"Origin", "Content-Type", "Accept"}
	r.Use(cors.New(config))

	// Register routes
	r.GET("/health", handlers.HealthCheck)
	r.POST("/calculate/indicators", handlers.CalculateIndicators)
	r.POST("/detect/patterns", handlers.DetectPatterns)
	r.POST("/analyze/smc", handlers.AnalyzeSMC)

	// Start server
	log.Println("🚀 Go Analysis API starting on :8001")
	if err := r.Run(":8001"); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}
