import yaml
import os


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

            # Удаление специфических метаданных OpenCV
            processed_lines = []
            for line in lines:
                if line.startswith('%YAML'):
                    continue
                processed_lines.append(line.replace('!!opencv-matrix', ''))

            content = "".join(processed_lines)
            data = yaml.safe_load(content)

        # Извлечение матрицы K и фокусного расстояния fx
        k_data = data['K']['data']
        focal_length = float(k_data[0])

        # Получение разрешения изображения (ширина, высота)
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
    # Определение путей относительно корня проекта
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../../"))

    file_name = "leftDef.yml"
    path = os.path.join(project_root, "ml_service", "data", "raw", file_name)

    print(f"Путь к файлу: {path}")

    calibration_data = parse_calibration(path)
    if calibration_data:
        print("\nПараметры калибровки:")
        print("-" * 30)
        print(f"Фокусное расстояние (fx): {calibration_data['focal_length']} px")
        print(f"Разрешение: {calibration_data['width']} x {calibration_data['height']}")
        print("-" * 30)