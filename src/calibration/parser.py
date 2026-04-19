import yaml
import os


def parse_calibration(file_path):
    """Парсит YAML файл калибровки камеры."""
    if not os.path.exists(file_path):
        return None

    with open(file_path, 'r') as f:
        # Убираем специфичную для OpenCV строку %YAML:1.0
        lines = f.readlines()
        content = "".join([l for l in lines if not l.startswith('%YAML')])
        data = yaml.safe_load(content)

    # Извлекаем данные
    k_matrix = data['K']['data']
    focal_length = k_matrix[0]  # fx
    width, height = data['sz']

    return {
        'focal_length': focal_length,
        'width': width,
        'height': height,
        'k_matrix': k_matrix
    }


if __name__ == "__main__":
    # Тестовый путь (исправь под свой файл)
    test_file = "data/raw/твой_файл.yml"
    print(parse_calibration(test_file))