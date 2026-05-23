package analysis

import "github.com/YaroslavnaKa/parking_3d_monitoring/backend_service/database"

// ParkingZone - структура границ парковочного пространства
type ParkingZone struct {
	LatStart float64
	LonStart float64
	LatEnd   float64
	LonEnd   float64
}

// CalculateFreeSpace - логика для вычисления свободного места (будет расширена на этапе построения карты)
func CalculateFreeSpace(zone ParkingZone, detections []database.FinalDetection) float64 {
	// Здесь будет алгоритм расчета расстояний между точками внутри зоны
	return 0.0
}
