package database

import (
	"fmt"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// FinalDetection - запись объекта в мировых координатах
type FinalDetection struct {
	gorm.Model
	FrameId   int     `json:"frame_id"`
	Latitude  float64 `json:"lat"`
	Longitude float64 `json:"lon"`
	ZDistance float64 `json:"z_dist"`
}

var DB *gorm.DB

// InitDB - инициализация и миграция базы данных
func InitDB() {
	var err error
	DB, err = gorm.Open(sqlite.Open("parking_monitoring.db"), &gorm.Config{})
	if err != nil {
		panic("Ошибка инициализации базы данных")
	}
	DB.AutoMigrate(&FinalDetection{})
	fmt.Println("База данных готова к работе")
}
