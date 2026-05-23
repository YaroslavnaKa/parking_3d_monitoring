# 3D Parking Occupancy Monitoring System

An automated system for urban parking space monitoring using monocular 3D object detection (Cube R-CNN) and sensor fusion with GPS/IMU telemetry.

***

## Project Overview
This project develops an intelligent system for monitoring parking availability using mobile sensors mounted on public transport (trams). By converting 2D video frames into a metric 3D space, the system localizes vehicles in global coordinates and identifies free parking spots in real-time.

### Key Features
* Monocular 3D Reconstruction: Powered by Omni3D (Cube R-CNN) to estimate vehicle dimensions and distance from a single camera feed.
* Sensor Fusion: Synchronizes high-frequency video frames with GPS/IMU telemetry using millisecond-precision timestamps.
* Intelligent Tracking and Filtering: Implements a 3D centroid tracker with EMA (Exponential Moving Average) smoothing to eliminate ghosting and filter out dynamic traffic.
* Automated Gap Analysis: Identifies available parking slots based on a 6.5m geometric standard.
* Interactive Mapping: Generates geospatial reports using Folium with WGS84 coordinate mapping.

---

## System Architecture
The project follows a hybrid microservice architecture to ensure high performance and scalability:

1. **ML Service (Python 3.10):**
   - Handles 3D inference and geometric class validation.
   - Performs temporal tracking for object stabilization.
   - Optimized for Apple Silicon (M4/MPS) using Metal Performance Shaders.

2. **Backend Service (Go 1.22):**
   - Manages data persistence via SQLite.
   - Handles complex coordinate transformations from Camera-Space to World-Space.
   - Implements stationarity logic to confirm parked vehicles.

---

## Installation

### Prerequisites
* OS: macOS (Apple Silicon recommended) or Linux.
* Python: 3.10 (strictly recommended for stability).
* Go: 1.22 or higher.

### 1. Setup ML Service
```bash
cd ml_service
pip install -r requirements.txt
```
*Note: PyTorch3D and Detectron2 must be built from source for M4 optimization.*

### 2. Setup Backend Service
```bash
cd backend_service
go mod tidy
```

---

## Usage

### Data Preparation
1. **Weights:** Place your model weights (e.g., `cubercnn_outdoor.pth`) in `ml_service/models/`
2. **Video:** Place `.avi` video episodes in `ml_service/data/raw/`
3. **Telemetry:** Place `cam.csv` and `gps.csv` logs in `backend_service/data/telemetry/`

### Execution Flow
**1. Start the Backend:**
```bash
cd backend_service
go run main.go
```

**2. Run the Batch Processor:**
```bash
cd ml_service/src/detection
python batch_processor.py
```

**3. Visualize Results:**
* Interactive Map: `python ml_service/src/visualization/build_map.py`
* Metrics Report: `python ml_service/src/metrics_calculator.py`

---

## Scientific Metrics and Results
The system has been evaluated using real-world data from Ligovsky Prospekt (Episodes 28-44). The following metrics demonstrate the system precision:

* **Localization Precision (RMSE):** 1.8647 meters (using standard GPS).
* **Average Confidence Score:** 41.58% (In-the-wild urban environment).
* **Traffic Filtration Efficiency:** 65% of moving objects were successfully identified and ignored.
* **Confirmed Stationary Objects:** 1,082 unique vehicles detected across the test set.

---