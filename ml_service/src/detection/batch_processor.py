import os
import sys
import torch
import cv2
import numpy as np
import json
import requests
from tqdm import tqdm

current_dir = os.path.dirname(os.path.abspath(__file__))
repo_path = os.path.join(current_dir, "omni3d_repo")
if repo_path not in sys.path:
    sys.path.insert(0, repo_path)

from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
from cubercnn.config.config import get_cfg_defaults
import cubercnn.modeling.meta_arch.rcnn3d
import cubercnn.modeling.roi_heads.cube_head
import cubercnn.modeling.backbone.resnet


def process_video_to_json(video_filename, focal_length=464.5, frame_offset=2284):
    """
    Пакетная обработка видео с передачей данных в Go-бэкенд.
    """
    cfg = get_cfg()
    get_cfg_defaults(cfg)
    cfg.merge_from_file(os.path.join(repo_path, "configs/cubercnn_ResNet34_FPN.yaml"))

    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 11
    cfg.MODEL.ROI_CUBE_HEAD.NUM_CLASSES = 11
    cfg.MODEL.WEIGHTS = os.path.join(current_dir, "../../models/cubercnn_outdoor.pth")
    cfg.MODEL.DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

    # Порог уверенности снижен для захвата большего количества объектов
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.2

    predictor = DefaultPredictor(cfg)

    video_path = os.path.join(current_dir, "../../data/raw/", video_filename)
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    K = np.array([[focal_length, 0, 483.1], [0, focal_length, 265.4], [0, 0, 1]], dtype=np.float32)
    all_frame_results = []

    print(f"Старт обработки: {video_filename}. Смещение кадров: {frame_offset}")

    for frame_idx in tqdm(range(total_frames)):
        ret, frame = cap.read()
        if not ret: break
        if frame_idx % 2 != 0: continue

        inputs = {"image": torch.as_tensor(frame.astype("float32").transpose(2, 0, 1)).to(cfg.MODEL.DEVICE),
                  "height": frame.shape[0], "width": frame.shape[1], "K": K}

        with torch.no_grad():
            outputs = predictor.model([inputs])[0]

        instances = outputs["instances"].to("cpu")
        current_frame_id = frame_idx + frame_offset

        frame_data = {"frame_id": current_frame_id, "objects": []}

        if len(instances) > 0 and instances.has("pred_bbox3D"):
            # Технический лог детекции
            print(f" Кадр {current_frame_id}: найдено объектов - {len(instances)}")

            centers = instances.pred_center_cam.numpy()
            for i in range(len(instances)):
                frame_data["objects"].append({
                    "class_id": int(instances.pred_classes[i]),
                    "position_cam": centers[i].tolist()
                })

        all_frame_results.append(frame_data)

    cap.release()

    # Отправка данных на локализацию
    try:
        print("Отправка пакета в бэкенд...")
        url = "http://localhost:8080/api/process_batch"
        res = requests.post(url, json=all_frame_results, timeout=60)
        if res.status_code == 200:
            print(f"Успешно. Объектов сохранено: {res.json().get('saved_objects')}")
    except Exception as e:
        print(f"Ошибка связи с бэкендом: {e}")


if __name__ == "__main__":
    process_video_to_json("new.003.028.left.avi", frame_offset=2284)