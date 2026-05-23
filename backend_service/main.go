package main

import (
	"fmt"
	"net/http"

	"github.com/YaroslavnaKa/parking_3d_monitoring/backend_service/analysis"
	"github.com/YaroslavnaKa/parking_3d_monitoring/backend_service/database"
	"github.com/YaroslavnaKa/parking_3d_monitoring/backend_service/telemetry"
	"github.com/gin-gonic/gin"
)

func main() {
	database.InitDB()
	telemetry.LoadAllTelemetry("data/telemetry")

	r := gin.Default()
	r.POST("/api/process_batch", func(c *gin.Context) {
		var frames []database.FrameInput
		if err := c.ShouldBindJSON(&frames); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
			return
		}
		saved := analysis.ProcessBatch(frames)
		fmt.Printf("Processed objects: %d\n", saved)
		c.JSON(http.StatusOK, gin.H{"saved_objects": saved})
	})

	r.Run(":8080")
}
