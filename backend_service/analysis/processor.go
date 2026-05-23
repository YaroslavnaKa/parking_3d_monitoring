package analysis

import (
	"math"

	"github.com/YaroslavnaKa/parking_3d_monitoring/backend_service/database"
	"github.com/YaroslavnaKa/parking_3d_monitoring/backend_service/geo"
	"github.com/YaroslavnaKa/parking_3d_monitoring/backend_service/telemetry"
)

const LateralOffset = 4.5

func ProcessBatch(frames []database.FrameInput) int {
	successCount := 0
	for _, frame := range frames {
		msec, exists := telemetry.CamSyncMap[frame.FrameId]
		if !exists {
			continue
		}
		gps := telemetry.FindClosestGps(msec)

		for _, obj := range frame.Objects {
			// Расчет координат с учетом бокового смещения
			xCorr := obj.PositionCam[0]
			side := "right"
			if xCorr < 0 {
				side = "left"
				xCorr -= LateralOffset
			} else {
				xCorr += LateralOffset
			}

			lat, lon := geo.ProjectToWorld(gps, xCorr, obj.PositionCam[2])

			// Поиск последней записи этого же объекта для расчета RMSE
			var lastSeen database.FinalDetection
			err := database.DB.Where("object_id = ?", obj.ObjectID).Order("frame_id desc").First(&lastSeen).Error

			isStatic := false
			currentRMSE := 0.0
			if err == nil {
				// Расчет отклонения координат между кадрами (метрика стабильности)
				currentRMSE = math.Sqrt(math.Pow(lat-lastSeen.Latitude, 2)+math.Pow(lon-lastSeen.Longitude, 2)) * 111132

				var count int64
				database.DB.Model(&database.FinalDetection{}).Where("object_id = ?", obj.ObjectID).Count(&count)
				// Если объект успешно сопровождается более 8 кадров, он считается стационарным
				if count >= 8 {
					isStatic = true
				}
			}

			database.DB.Create(&database.FinalDetection{
				FrameId:      frame.FrameId,
				ObjectID:     obj.ObjectID,
				ClassId:      obj.ClassId,
				Latitude:     lat,
				Longitude:    lon,
				CamX:         obj.PositionCam[0],
				CamZ:         obj.PositionCam[2],
				Yaw:          obj.Yaw,
				IsStationary: isStatic,
				Side:         side,
				Confidence:   obj.Confidence,
				RMSE:         currentRMSE,
			})
			successCount++
		}
	}
	return successCount
}
