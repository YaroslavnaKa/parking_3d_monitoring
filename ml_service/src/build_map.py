import sqlite3
import folium
import os


def generate_parking_map():
    """
    Генерация карты на основе данных из SQLite.
    """
    # 1. Определение путей (учитывая, что скрипт в ml_service/src/)
    current_script_path = os.path.abspath(__file__)
    # Поднимаемся на 2 уровня вверх: src -> ml_service -> Project_Root
    src_dir = os.path.dirname(current_script_path)
    ml_service_dir = os.path.dirname(src_dir)
    project_root = os.path.dirname(ml_service_dir)

    # Путь к базе данных в соседнем сервисе
    db_path = os.path.join(project_root, "backend_service", "parking_monitoring.db")

    print(f"Поиск базы данных по адресу: {db_path}")

    if not os.path.exists(db_path):
        print(f"ОШИБКА: Файл {db_path} не найден.")
        return

    # 2. Подключение к БД и извлечение координат
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Проверка наличия таблицы и данных
        cursor.execute("SELECT latitude, longitude, z_distance, frame_id FROM final_detections")
        points = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"ОШИБКА БД: {e}")
        return

    if not points:
        print("В таблице нет данных для отображения.")
        return

    print(f"Успех! Найдено точек: {len(points)}")

    # 3. Инициализация карты (центрирование на первой точке)
    start_coords = [points[0][0], points[0][1]]
    parking_map = folium.Map(location=start_coords, zoom_start=21, tiles='OpenStreetMap')

    # 4. Добавление маркеров на карту
    for p in points:
        lat, lon, dist, frame = p
        folium.CircleMarker(
            location=[lat, lon],
            radius=2,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.7,
            popup=f"Кадр: {frame}, Z: {dist:.1f}м"
        ).add_to(parking_map)

    # 5. Сохранение результата в корень проекта
    output_path = os.path.join(project_root, "parking_space_map.html")
    parking_map.save(output_path)
    print(f"Карта создана и сохранена: {output_path}")

    conn.close()


if __name__ == "__main__":
    generate_parking_map()