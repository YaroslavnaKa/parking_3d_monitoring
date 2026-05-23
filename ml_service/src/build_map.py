import sqlite3
import folium
import os
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import math

# --- ГЕО-ГРАНИЦЫ ИЗ ТЗ (Лиговский проспект) ---
LAT_MIN, LAT_MAX = 59.915973, 59.925523
LON_MIN, LON_MAX = 30.350783, 30.357227

# --- НАСТРОЙКИ СТАНДАРТА ---
AVG_CAR_LEN = 4.5  # Длина машины
HALF_CAR = AVG_CAR_LEN / 2
REQUIRED_GAP = 6.0  # Чистое место для втискивания авто
SIDE_OFFSET_METERS = 4.8  # Смещение от рельс


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlam = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(max(0, a)))


def get_root():
    p = os.path.abspath(__file__)
    while os.path.basename(p) != "parking_3d_monitoring": p = os.path.dirname(p)
    return p


def get_curb_pt(t_lat, t_lon, t_yaw, side):
    angle = t_yaw + (math.pi / 2 if side == 'right' else -math.pi / 2)
    dist_lat = (SIDE_OFFSET_METERS / 111132.0) * math.cos(angle)
    dist_lon = (SIDE_OFFSET_METERS / (111132.0 * math.cos(math.radians(t_lat)))) * math.sin(angle)
    return t_lat + dist_lat, t_lon + dist_lon


def find_index_at_dist(path, start_idx, target_dist, direction=1):
    """Ищет индекс точки на пути, находящейся на расстоянии target_dist от start_idx."""
    curr_dist = 0
    curr_idx = start_idx
    while 0 <= curr_idx + direction < len(path):
        p1 = path[curr_idx]
        p2 = path[curr_idx + direction]
        curr_dist += haversine(p1[0], p1[1], p2[0], p2[1])
        curr_idx += direction
        if curr_dist >= target_dist:
            return curr_idx
    return curr_idx


def generate_map():
    root = get_root()
    db_path = os.path.join(root, "parking_monitoring.db")
    telemetry_dir = os.path.join(root, "backend_service/data/telemetry")

    # 1. Загрузка и обрезка траектории
    gps_files = [f for f in os.listdir(telemetry_dir) if "gps" in f and f.endswith(".csv")]
    df_gps = pd.read_csv(os.path.join(telemetry_dir, gps_files[0]))
    for col in ['nord', 'east', 'yaw']: df_gps[col] = pd.to_numeric(df_gps[col], errors='coerce')
    df_gps = df_gps.dropna(subset=['nord', 'east', 'yaw'])
    df_gps = df_gps[(df_gps['nord'] >= LAT_MIN) & (df_gps['nord'] <= LAT_MAX)]
    tram_path = df_gps[['nord', 'east', 'yaw']].values

    # 2. Загрузка машин
    conn = sqlite3.connect(db_path)
    df_cars = pd.read_sql_query(
        "SELECT latitude, longitude, side FROM final_detections WHERE is_stationary = 1 AND class_id != 6", conn)
    conn.close()

    m = folium.Map(location=[(LAT_MIN + LAT_MAX) / 2, (LON_MIN + LON_MAX) / 2], zoom_start=18, tiles='cartodbpositron')

    for side in ['left', 'right']:
        side_data = df_cars[df_cars['side'] == side]
        color = 'blue' if side == 'left' else 'purple'

        if side_data.empty:
            # Если машин нет, рисуем всю линию как свободную
            full_path = [get_curb_pt(p[0], p[1], p[2], side) for p in tram_path]
            folium.PolyLine(full_path, color='green', weight=8, opacity=0.4).add_to(m)
            continue

        # Кластеризация машин
        coords = side_data[['latitude', 'longitude']].values.astype(float)
        cls = DBSCAN(eps=2.5 / 6371000, min_samples=1).fit(np.radians(coords))

        unique_cars = []
        for c_id in set(cls.labels_):
            center = coords[cls.labels_ == c_id].mean(axis=0)
            dists_sq = np.sum((tram_path[:, :2] - center) ** 2, axis=1)
            idx = np.argmin(dists_sq)
            t_lat, t_lon, t_yaw = tram_path[idx]
            curb_pos = get_offset_point = get_curb_pt(t_lat, t_lon, t_yaw, side)
            unique_cars.append({'idx': idx, 'coords': curb_pos})
            folium.CircleMarker(location=curb_pos, radius=4, color=color, fill=True).add_to(m)

        unique_cars.sort(key=lambda x: x['idx'])

        # --- РАСЧЕТ СВОБОДНЫХ МЕСТ (ГЕОМЕТРИЧЕСКИЙ) ---

        # 1. От начала зоны до первой машины
        first_car_idx = unique_cars[0]['idx']
        start_gap_idx = find_index_at_dist(tram_path, first_car_idx, HALF_CAR, direction=-1)
        if start_gap_idx > 20:  # Проверяем, есть ли место в начале
            gap_path = [get_curb_pt(tram_path[p][0], tram_path[p][1], tram_path[p][2], side) for p in
                        range(0, start_gap_idx)]
            folium.PolyLine(gap_path, color='green', weight=10, opacity=0.6).add_to(m)

        # 2. Между машинами
        for i in range(len(unique_cars) - 1):
            c1_idx = unique_cars[i]['idx']
            c2_idx = unique_cars[i + 1]['idx']

            # Расстояние по траектории
            dist_m = haversine(unique_cars[i]['coords'][0], unique_cars[i]['coords'][1],
                               unique_cars[i + 1]['coords'][0], unique_cars[i + 1]['coords'][1])

            # Чистое место = Дистанция - (половина машины 1 + половина машины 2)
            if (dist_m - AVG_CAR_LEN) >= REQUIRED_GAP:
                # Находим точки "бамперов"
                idx_s = find_index_at_dist(tram_path, c1_idx, HALF_CAR, direction=1)
                idx_e = find_index_at_dist(tram_path, c2_idx, HALF_CAR, direction=-1)

                if idx_e > idx_s:
                    gap_path = [get_curb_pt(tram_path[p][0], tram_path[p][1], tram_path[p][2], side) for p in
                                range(idx_s, idx_e + 1)]
                    folium.PolyLine(gap_path, color='green', weight=10, opacity=0.6).add_to(m)

        # 3. От последней машины до конца зоны
        last_car_idx = unique_cars[-1]['idx']
        end_gap_idx = find_index_at_dist(tram_path, last_car_idx, HALF_CAR, direction=1)
        if len(tram_path) - 1 > end_gap_idx + 20:
            gap_path = [get_curb_pt(tram_path[p][0], tram_path[p][1], tram_path[p][2], side) for p in
                        range(end_gap_idx, len(tram_path))]
            folium.PolyLine(gap_path, color='green', weight=10, opacity=0.6).add_to(m)

    save_path = os.path.join(root, "final_parking_map.html")
    m.save(save_path)
    print(f"Карта обновлена: {save_path}")


if __name__ == "__main__":
    generate_map()