import os
import sys
import torch
import cv2
import numpy as np
import requests
from tqdm import tqdm
from scipy.spatial import distance
from collections import OrderedDict

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

K = np.array([[1305.0, 0, 472.9], [0, 1305.0, 265.2], [0, 0, 1]], dtype=np.float32)

CLASS_MAP = {
    0: "Car",
    1: "Truck",
    6: "Person"
}

PURPLE_BGR = (128, 0, 128)
SMOOTHING = 0.4

def refine_class(cls_id, dims):
    h, w, l = dims
    if l > 6.2 or h > 2.1:
        return 1
    if l < 2.0 or w < 0.9:
        return 6
    if h < 2.0 and l < 6.0:
        return 0
    return cls_id

class Simple3DTracker:
    def __init__(self, max_distance=5.0):
        self.next_id = 0
        self.objects = {}
        self.max_distance = max_distance

    def update(self, detections):
        if not detections:
            self.objects = {}
            return {}
        input_centers = np.array([d['center'] for d in detections])
        if not self.objects:
            new_objects = {}
            for d in detections:
                new_objects[self.next_id] = {**d}
                self.next_id += 1
            self.objects = new_objects
        else:
            obj_ids = list(self.objects.keys())
            obj_centers = np.array([self.objects[oid]['center'] for oid in obj_ids])
            D = distance.cdist(obj_centers, input_centers)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]
            used_rows, used_cols = set(), set()
            new_objects = {}
            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols: continue
                if D[row, col] > self.max_distance: continue
                obj_id = obj_ids[row]
                new_pos = (1 - SMOOTHING) * self.objects[obj_id]['center'] + SMOOTHING * detections[col]['center']
                new_objects[obj_id] = {
                    'center': new_pos, 'dims': detections[col]['dims'],
                    'yaw': detections[col]['yaw'], 'cls': detections[col]['cls'], 'conf': detections[col]['conf']
                }
                used_rows.add(row); used_cols.add(col)
            for i in range(len(input_centers)):
                if i not in used_cols:
                    new_objects[self.next_id] = {**detections[i]}
                    self.next_id += 1
            self.objects = new_objects
        return self.objects

def get_3d_corners(center, dims, yaw):
    h, w, l = dims
    x, y, z = center
    base_y = y + h/2
    R = np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]])
    pts = np.array([[w/2, 0, l/2], [w/2, 0, -l/2], [-w/2, 0, -l/2], [-w/2, 0, l/2],
                    [w/2, -h, l/2], [w/2, -h, -l/2], [-w/2, -h, -l/2], [-w/2, -h, l/2]])
    return np.dot(R, pts.T).T + [x, base_y, z]

def project_to_2d(pts_3d):
    pts_2d = np.dot(K, pts_3d.T).T
    pts_2d[:, 0] /= (pts_2d[:, 2] + 1e-6); pts_2d[:, 1] /= (pts_2d[:, 2] + 1e-6)
    return pts_2d[:, :2].astype(np.int32)

def draw_visuals(img, pts_2d, label, dist):
    for i in range(4):
        cv2.line(img, tuple(pts_2d[i]), tuple(pts_2d[(i+1)%4]), PURPLE_BGR, 2)
        cv2.line(img, tuple(pts_2d[i+4]), tuple(pts_2d[(i+1)%4 + 4]), PURPLE_BGR, 2)
        cv2.line(img, tuple(pts_2d[i]), tuple(pts_2d[i+4]), PURPLE_BGR, 2)
    cv2.putText(img, f"{label} {dist:.1f}m", (pts_2d[4][0], pts_2d[4][1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

def get_predictor():
    cfg = get_cfg()
    get_cfg_defaults(cfg)
    cfg.merge_from_file(os.path.join(repo_path, "configs/cubercnn_ResNet34_FPN.yaml"))
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 11
    cfg.MODEL.ROI_CUBE_HEAD.NUM_CLASSES = 11
    cfg.MODEL.WEIGHTS = os.path.join(current_dir, "../../models/cubercnn_outdoor.pth")
    cfg.MODEL.DEVICE = "mps"
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.25
    return DefaultPredictor(cfg)

def run_sync_extraction():
    predictor = get_predictor()
    tracker = Simple3DTracker()
    raw_dir = os.path.join(current_dir, "../../data/raw")
    video_files = sorted([f for f in os.listdir(raw_dir) if f.endswith(".avi")])
    current_fid = 2284
    root_path = os.path.abspath(os.path.join(current_dir, "../../../"))
    video_output = os.path.join(root_path, "final_processed_output.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_writer = None

    for v_name in video_files:
        cap = cv2.VideoCapture(os.path.join(raw_dir, v_name))
        frame_results = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            if out_writer is None:
                h, w = frame.shape[:2]
                out_writer = cv2.VideoWriter(video_output, fourcc, 10.0, (w, h))
            draw_frame = frame.copy()
            inputs = {"image": torch.as_tensor(frame.astype("float32").transpose(2, 0, 1)).to("mps"),
                      "height": 540, "width": 960, "K": K}
            with torch.no_grad():
                out = predictor.model([inputs])[0]
            inst = out["instances"].to("cpu")
            dets = []
            if len(inst) > 0 and inst.has("pred_bbox3D"):
                centers, dims, yaws, classes, scores = inst.pred_center_cam.numpy(), inst.pred_dimensions.numpy(), inst.pred_pose.numpy(), inst.pred_classes.numpy(), inst.scores.numpy()
                for i in range(len(inst)):
                    if centers[i][2] > 1.5:
                        rc = refine_class(int(classes[i]), dims[i])
                        dets.append({'center': centers[i], 'dims': dims[i], 'yaw': float(yaws[i].flatten()[-1].item()), 'cls': rc, 'conf': float(scores[i])})
            tracked_objects = tracker.update(dets)
            frame_data = {"frame_id": current_fid + len(frame_results), "objects": []}
            for oid, obj in tracked_objects.items():
                pts_2d = project_to_2d(get_3d_corners(obj['center'], obj['dims'], obj['yaw']))
                label = CLASS_MAP.get(obj['cls'], "Object")
                draw_visuals(draw_frame, pts_2d, label, obj['center'][2])
                frame_data["objects"].append({
                    "object_id": oid, "class_id": obj['cls'],
                    "position_cam": obj['center'].tolist(), "yaw": obj['yaw'], "confidence": obj['conf']
                })
            frame_results.append(frame_data)
            out_writer.write(draw_frame)
            cv2.imshow("3D Monitoring", draw_frame)
            if cv2.waitKey(100) & 0xFF == ord('q'): break
        cap.release()
        current_fid += len(frame_results)
        try:
            requests.post("http://localhost:8080/api/process_batch", json=frame_results)
        except: pass
    if out_writer: out_writer.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_sync_extraction()