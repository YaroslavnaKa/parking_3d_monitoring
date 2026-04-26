package geo

import (
	"math"

	"github.com/YaroslavnaKa/parking_3d_monitoring/backend_service/telemetry"
)

// ProjectToWorld - перевод локальных координат камеры в WGS84
func ProjectToWorld(gps telemetry.GpsEntry, xCam, zCam float64) (float64, float64) {
	const metersPerDegree = 111132.0

	// Поворот координат на угол Yaw
	angle := gps.Yaw
	worldX := xCam*math.Cos(angle) - zCam*math.Sin(angle)
	worldY := xCam*math.Sin(angle) + zCam*math.Cos(angle)

	finalLat := gps.Lat + (worldY / metersPerDegree)
	finalLon := gps.Lon + (worldX / (metersPerDegree * math.Cos(gps.Lat*math.Pi/180)))

	return finalLat, finalLon
}
