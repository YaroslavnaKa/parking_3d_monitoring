package database

import (
	"fmt"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type FinalDetection struct {
	gorm.Model
	FrameId      int     `json:"frame_id"`
	ObjectID     int     `json:"object_id"`
	ClassId      int     `json:"class_id"`
	Latitude     float64 `json:"lat"`
	Longitude    float64 `json:"lon"`
	CamX         float64 `json:"cam_x"`
	CamZ         float64 `json:"cam_z"`
	Yaw          float64 `json:"yaw"`
	IsStationary bool    `json:"is_stationary"`
	Side         string  `json:"side"`
	Confidence   float64 `json:"confidence"`
	RMSE         float64 `json:"rmse"`
}

type DetectionObject struct {
	ClassId     int       `json:"class_id"`
	ObjectID    int       `json:"object_id"`
	PositionCam []float64 `json:"position_cam"`
	Yaw         float64   `json:"yaw"`
	Confidence  float64   `json:"confidence"`
}

type FrameInput struct {
	FrameId int               `json:"frame_id"`
	Objects []DetectionObject `json:"objects"`
}

var DB *gorm.DB

func InitDB() {
	var err error
	// База данных создается в корне проекта
	DB, err = gorm.Open(sqlite.Open("../parking_monitoring.db"), &gorm.Config{})
	if err != nil {
		panic("Database connection failed")
	}
	DB.AutoMigrate(&FinalDetection{})
	fmt.Println("Database schema updated")
}
