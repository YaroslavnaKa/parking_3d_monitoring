package telemetry

import (
	"encoding/csv"
	"fmt"
	"io"
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
	GpsLog     = []GpsEntry{}
)

func LoadAllTelemetry(dir string) {
	files, _ := filepath.Glob(filepath.Join(dir, "*.csv"))
	CamSyncMap = make(map[int]int64)
	GpsLog = []GpsEntry{}

	fmt.Println("=== Поиск файлов телеметрии ===")
	for _, file := range files {
		fname := strings.ToLower(filepath.Base(file))
		if strings.HasPrefix(fname, "cam") {
			loadCamFile(file)
		} else if strings.HasPrefix(fname, "gps") {
			loadGpsFile(file)
		}
	}
	fmt.Printf("\nИТОГ: Кадров синхронизировано: %d, Точек GPS найдено: %d\n", len(CamSyncMap), len(GpsLog))
}

func loadCamFile(path string) {
	f, _ := os.Open(path)
	defer f.Close()
	r := csv.NewReader(f)
	for {
		line, err := r.Read()
		if err == io.EOF { break }
		if len(line) < 2 || line[0] == "grabNumber" { continue }
		fId, _ := strconv.Atoi(line[0])
		msec, _ := strconv.ParseInt(line[1], 10, 64)
		CamSyncMap[fId] = msec
	}
	fmt.Printf("✓ Загружен файл камер: %s\n", filepath.Base(path))
}

func loadGpsFile(path string) {
	f, _ := os.Open(path)
	defer f.Close()
	r := csv.NewReader(f)
	count := 0
	for {
		line, err := r.Read()
		if err == io.EOF { break }
		if len(line) < 23 || line[0] == "nord" { continue }
		lat, _ := strconv.ParseFloat(line[0], 64)
		lon, _ := strconv.ParseFloat(line[1], 64)
		yaw, _ := strconv.ParseFloat(line[7], 64)
		msec, _ := strconv.ParseInt(line[22], 10, 64)
		GpsLog = append(GpsLog, GpsEntry{GrabMsec: msec, Lat: lat, Lon: lon, Yaw: yaw})
		count++
	}
	fmt.Printf("✓ Загружен файл GPS: %s (%d точек)\n", filepath.Base(path), count)
}

func FindClosestGps(targetMsec int64) GpsEntry {
	if len(GpsLog) == 0 { return GpsEntry{} }
	best := GpsLog[0]
	minDiff := int64(9999999)
	for _, entry := range GpsLog {
		diff := targetMsec - entry.GrabMsec
		if diff < 0 { diff = -diff }
		if diff < minDiff {
			minDiff = diff
			best = entry
		}
	}
	return best
}