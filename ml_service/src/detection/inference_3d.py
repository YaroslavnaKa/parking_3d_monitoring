import os
import sys
import torch
import cv2
import numpy as np

# Настройка путей для доступа к модулям cubercnn
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_path = os.path.join(current_dir, "omni3d_repo")
if repo_path not in sys.path:
    sys.path.insert(0, repo_path)

from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor

# Регистрация компонентов архитектуры
from cubercnn.config.config import get_cfg_defaults
import cubercnn.modeling.meta_arch.rcnn3d
import cubercnn.modeling.roi_heads.cube_head
import cubercnn.modeling.backbone.resnet
import cubercnn.modeling.backbone.dla


def get_3d_box_corners(center, dims, yaw):
    """
    Вычисление 8 вершин 3D параллелепипеда.
    center: [x, y, z], dims: [l, w, h], yaw: угол поворота в радианах.
    """
    l, w, h = dims
    # Координаты вершин в локальной системе объекта
    x_corners = [l / 2, l / 2, -l / 2, -l / 2, l / 2, l / 2, -l / 2, -l / 2]
    y_corners = [w / 2, -w / 2, -w / 2, w / 2, w / 2, -w / 2, -w / 2, w / 2]
    z_corners = [h / 2, h / 2, h / 2, h / 2, -h / 2, -h / 2, -h / 2, -h / 2]

    # Матрица поворота вокруг вертикальной оси Y
    R = np.array([
        [np.cos(yaw), 0, np.sin(yaw)],
        [0, 1, 0],
        [-np.sin(yaw), 0, np.cos(yaw)]
    ])

    corners_3d = np.vstack([x_corners, y_corners, z_corners])
    corners_3d = np.dot(R, corners_3d).T
    corners_3d = corners_3d + center
    return corners_3d


def project_3d_to_2d(corners_3d, K):
    """
    Проекция 3D точек на плоскость изображения (2D пиксели).
    """
    # corners_3d: [8, 3], K: [3, 3]
    pts_2d = np.dot(K, corners_3d.T).T
    pts_2d[:, 0] /= pts_2d[:, 2]
    pts_2d[:, 1] /= pts_2d[:, 2]
    return pts_2d[:, :2].astype(np.int32)


def draw_cube(img, pts, color=(0, 255, 255)):
    """
    Отрисовка ребер спроецированного куба.
    """
    # Соединение нижнего и верхнего оснований
    for i in range(4):
        cv2.line(img, tuple(pts[i]), tuple(pts[(i + 1) % 4]), color, 2)
        cv2.line(img, tuple(pts[i + 4]), tuple(pts[((i + 1) % 4) + 4]), color, 2)
        cv2.line(img, tuple(pts[i]), tuple(pts[i + 4]), color, 2)


def run_inference():
    """
    Основной цикл детекции и визуализации 3D данных.
    """
    cfg = get_cfg()
    get_cfg_defaults(cfg)
    cfg.merge_from_file(os.path.join(repo_path, "configs/cubercnn_ResNet34_FPN.yaml"))

    # Конфигурация для Outdoor модели (11 классов)
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 11
    cfg.MODEL.ROI_CUBE_HEAD.NUM_CLASSES = 11
    cfg.MODEL.WEIGHTS = os.path.join(current_dir, "../../models/cubercnn_outdoor.pth")

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    cfg.MODEL.DEVICE = device
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5

    print(f"Инициализация модели на устройстве: {device}")
    predictor = DefaultPredictor(cfg)

    # Чтение кадра
    video_path = os.path.join(current_dir, "../../data/raw/new.003.028.left.avi")
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    if not ret: return

    # Параметры калибровки
    f_len = 464.5
    cx, cy = 483.1, 265.4
    K = np.array([[f_len, 0, cx], [0, f_len, cy], [0, 0, 1]], dtype=np.float32)

    # Подготовка входного тензора
    image_tensor = torch.as_tensor(frame.astype("float32").transpose(2, 0, 1)).to(device)
    inputs = {"image": image_tensor, "height": frame.shape[0], "width": frame.shape[1], "K": K}

    print("Выполнение 3D детекции...")
    with torch.no_grad():
        outputs = predictor.model([inputs])[0]

    instances = outputs["instances"].to("cpu")
    num_found = len(instances)
    print(f"Обнаружено объектов: {num_found}")

    if num_found > 0 and instances.has("pred_bbox3D"):
        # Извлечение тензоров результатов
        centers = instances.pred_center_cam.numpy()
        dimensions = instances.pred_dimensions.numpy()
        poses = instances.pred_pose.numpy()  # Включает yaw в конце или как матрицу

        for i in range(num_found):
            # Расчет угла поворота (yaw) из предсказанной позы
            # В Cube R-CNN yaw обычно находится в последнем столбце или рассчитывается из матрицы
            yaw = poses[i][-1] if poses[i].ndim == 1 else 0

            # 1. Получение 3D координат вершин
            corners_3d = get_3d_box_corners(centers[i], dimensions[i], yaw)

            # 2. Проекция на 2D плоскость кадра
            pts_2d = project_3d_to_2d(corners_3d, K)

            # 3. Визуализация и логирование
            z_depth = centers[i][2]
            print(f"Объект {i + 1}: Дистанция Z = {z_depth:.2f} м")

            draw_cube(frame, pts_2d)

            # Индикация дистанции на кадре
            box = instances.pred_boxes.tensor[i].numpy()
            cv2.putText(frame, f"{z_depth:.1f}m", (int(box[0]), int(box[1] - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("Omni3D - Manual Projection Result", frame)
    print("Процесс завершен. Нажмите любую клавишу для закрытия.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_inference()