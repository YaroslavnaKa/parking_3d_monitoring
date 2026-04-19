import yaml
import os
import requests  # Добавлен импорт для отправки данных


def parse_calibration(file_path):
    """
    Парсинг YAML файлов калибровки камеры.
    Обработка тегов OpenCV для совместимости с PyYAML.
    """
    if not os.path.exists(file_path):
        print(f"Файл не найден: {file_path}")
        return None

    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            processed_lines = []
            for line in lines:
                if line.startswith('%YAML'):
                    continue
                processed_lines.append(line.replace('!!opencv-matrix', ''))

            content = "".join(processed_lines)
            data = yaml.safe_load(content)

        k_data = data['K']['data']
        focal_length = float(k_data[0])
        width, height = data['sz']

        return {
            'focal_length': focal_length,
            'width': width,
            'height': height,
            'k_matrix': k_data
        }
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return None


if __name__ == "__main__":
    # Настройка путей
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
    file_name = "leftDef.yml"
    path = os.path.join(project_root, "ml_service", "data", "raw", file_name)

    # Получение данных калибровки
    calibration_data = parse_calibration(path)

    if calibration_data:
        print(f"Извлечено фокусное расстояние: {calibration_data['focal_length']} px")

        # Подготовка данных для отправки в Go-бэкенд
        payload = {
            "focal_length": calibration_data['focal_length'],
            "width": calibration_data['width'],
            "height": calibration_data['height']
        }

        # Отправка POST-запроса на локальный сервер Go
        try:
            url = "http://localhost:8080/api/detections"
            response = requests.post(url, json=payload)

            if response.status_code == 200:
                print("Интеграционный тест пройден: данные успешно переданы в Go-бэкенд!")
            else:
                print(f"Ошибка связи с бэкендом. Статус: {response.status_code}")
        except Exception as e:
            print(f"Бэкенд недоступен. Убедитесь, что сервер в GoLand запущен. Ошибка: {e}")