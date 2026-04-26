package main

import (
	"fmt"
	"net/http"

	"github.com/YaroslavnaKa/parking_3d_monitoring/backend_service/database"
	"github.com/YaroslavnaKa/parking_3d_monitoring/backend_service/geo"
	"github.com/YaroslavnaKa/parking_3d_monitoring/backend_service/telemetry"
	"github.com/gin-gonic/gin"
)

type DetectionObject struct {
	ClassId     int       `json:"class_id"`
	PositionCam []float64 `json:"position_cam"`
}

type FrameInput struct {
	FrameId int               `json:"frame_id"`
	Objects []DetectionObject `json:"objects"`
}

func main() {
	database.InitDB()
	telemetry.LoadAllTelemetry("data/telemetry")

	r := gin.Default()

	r.POST("/api/process_batch", func(c *gin.Context) {
		var frames []FrameInput
		if err := c.ShouldBindJSON(&frames); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "bad json"})
			return
		}

		successCount := 0
		notFoundInCam := 0

		for _, frame := range frames {
			msec, exists := telemetry.CamSyncMap[frame.FrameId]
			if !exists {
				notFoundInCam++
				continue
			}

			if len(frame.Objects) == 0 {
				continue
			}

			gps := telemetry.FindClosestGps(msec)

			for _, obj := range frame.Objects {
				lat, lon := geo.ProjectToWorld(gps, obj.PositionCam[0], obj.PositionCam[2])
				database.DB.Create(&database.FinalDetection{
					FrameId:   frame.FrameId,
					Latitude:  lat,
					Longitude: lon,
					ZDistance: obj.PositionCam[2],
				})
				successCount++
			}
		}

		fmt.Printf("Получено кадров: %d. Ошибок синхронизации: %d. Сохранено объектов: %d.\n", len(frames), notFoundInCam, successCount)
		c.JSON(http.StatusOK, gin.H{"saved_objects": successCount})
	})

	r.Run(":8080")
}
