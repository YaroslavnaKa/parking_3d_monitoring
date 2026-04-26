package telemetry

import (
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

type GpsEntry struct {
	GrabMsec int64
	Lat      float64
	Lon      float64
	Yaw      float64
}

var (
	CamSyncMap = make(map[int]int64)
	GpsLog     []GpsEntry
)

func LoadAllTelemetry(dir string) {
	files, _ := filepath.Glob(filepath.Join(dir, "*.csv"))

	// Очистка старых данных перед загрузкой
	CamSyncMap = make(map[int]int64)
	GpsLog = []GpsEntry{}

	for _, file := range files {
		if strings.Contains(file, "cam") {
			loadCam(file)
		} else if strings.Contains(file, "gps") {
			loadGps(file)
		}
	}
	fmt.Printf("Итог загрузки телеметрии: Кадров: %d, Точек GPS: %d\n", len(CamSyncMap), len(GpsLog))
}

func loadCam(path string) {
	f, err := os.Open(path)
	if err != nil {
		return
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.Comma = ',' // Установлен разделитель "запятая" согласно скриншоту

	count := 0
	for {
		line, err := r.Read()
		if err == io.EOF {
			break
		}
		if len(line) < 2 || line[0] == "grabNumber" {
			continue
		}

		fId, _ := strconv.Atoi(line[0])
		msec, _ := strconv.ParseInt(line[1], 10, 64)
		CamSyncMap[fId] = msec
		count++
	}
	fmt.Printf("Обработан файл синхронизации: %s (%d строк)\n", filepath.Base(path), count)
}

func loadGps(path string) {
	f, err := os.Open(path)
	if err != nil {
		return
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.Comma = ',' // Установлен разделитель "запятая"

	count := 0
	for {
		line, err := r.Read()
		if err == io.EOF {
			break
		}
		if len(line) < 23 || line[0] == "nord" {
			continue
		}

		lat, _ := strconv.ParseFloat(line[0], 64)
		lon, _ := strconv.ParseFloat(line[1], 64)
		yaw, _ := strconv.ParseFloat(line[7], 64)
		msec, _ := strconv.ParseInt(line[22], 10, 64)

		GpsLog = append(GpsLog, GpsEntry{GrabMsec: msec, Lat: lat, Lon: lon, Yaw: yaw})
		count++
	}
	fmt.Printf("Обработан файл GPS: %s (%d точек)\n", filepath.Base(path), count)
}

func FindClosestGps(targetMsec int64) GpsEntry {
	if len(GpsLog) == 0 {
		return GpsEntry{}
	}
	best := GpsLog[0]
	minDiff := math.Abs(float64(targetMsec - best.GrabMsec))
	for _, entry := range GpsLog {
		diff := math.Abs(float64(targetMsec - entry.GrabMsec))
		if diff < minDiff {
			minDiff = diff
			best = entry
		}
	}
	return best
}
