"""YOLO 평가 · 예측 공통 기능 (src/evaluate_detector.py).

Baseline 평가와 Improved 평가가 같은 함수를 쓴다.
→ 두 모델의 차이는 "넘겨 준 가중치" 하나뿐이어야 한다 (같은 Validation · 같은 기준).

여기서는 계산만 한다. 검사 · 파일 정리 · 기록은 실행 스크립트(scripts/)가 맡는다.

    evaluate_detector()  Validation 지표 (Precision · Recall · mAP) + Confusion Matrix 그림
    predict_images()     이미지 폴더 예측 → (파일명, 크기, 예측 박스) 를 한 장씩 돌려줌
    match_boxes()        한 장의 정답(GT) · 예측 박스를 짝지어 TP · FP · FN 을 센다 (화면 · GPU 없이 테스트 가능)
"""
from pathlib import Path

# Frozen Test 는 Final Model 을 고른 뒤 Final 선정 단계에 한 번만
ALLOWED_SPLITS = ("val",)


def evaluate_detector(model_path: str, data_yaml: str, split: str, imgsz: int, batch: int,
                      project: Path, name: str, allow_test: bool = False):
    """model.val() 실행. 돌려주는 값: (metrics, 결과 폴더 Path)

    split 은 기본적으로 "val" 만 허용한다. "test" 는 allow_test=True 를 명시해야 한다 (Final 선정 단계 전용).
    """
    if split not in ALLOWED_SPLITS and not (split == "test" and allow_test):
        raise ValueError(f"평가 split 은 val 만 허용합니다 (Frozen Test 보호): {split}")
    if not Path(project).is_absolute():
        raise ValueError(f"project 는 절대경로여야 합니다: {project}")
    from ultralytics import YOLO                      # 검사를 통과한 뒤에만 import (검사 · 테스트 때는 불필요)

    model = YOLO(model_path)
    metrics = model.val(data=data_yaml, split=split, imgsz=imgsz, batch=batch, plots=True,
                        project=str(project), name=name, exist_ok=True)   # 평가는 다시 해도 같은 결과 → 덮어쓰기 허용
    return metrics, Path(metrics.save_dir)


def predict_images(model_path: str, source: Path, conf: float, imgsz: int, project: Path, name: str):
    """이미지 폴더 예측 (박스 그린 이미지는 project/name 에 저장 · Git 제외 폴더).

    한 장씩 돌려준다: (파일명, (너비, 높이), [(cls, conf, x, y, w, h), ...])   좌표는 0~1 (YOLO 형식)
    """
    from ultralytics import YOLO

    if not Path(project).is_absolute():
        raise ValueError(f"project 는 절대경로여야 합니다: {project}")
    model = YOLO(model_path)
    for r in model.predict(source=str(source), conf=conf, imgsz=imgsz, save=True, stream=True, verbose=False,
                           project=str(project), name=name, exist_ok=True):
        h, w = r.orig_shape
        boxes = [(int(c), float(s), *map(float, b))
                 for c, s, b in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xywhn.tolist())]
        yield Path(r.path).name, (w, h), boxes


def iou_xywh(a, b) -> float:
    """중심 · 크기(0~1) 박스 두 개의 IoU. (가로 · 세로를 따로 늘려도 IoU 는 같아서 0~1 좌표로 계산해도 된다)"""
    ax1, ay1, ax2, ay2 = a[0] - a[2] / 2, a[1] - a[3] / 2, a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1, bx2, by2 = b[0] - b[2] / 2, b[1] - b[3] / 2, b[0] + b[2] / 2, b[1] + b[3] / 2
    iw, ih = max(0.0, min(ax2, bx2) - max(ax1, bx1)), max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def match_boxes(gts, preds, iou_thr: float = 0.5) -> dict:
    """한 장의 GT 와 예측을 짝짓는다 (점수 높은 예측부터 · 한 GT 는 한 번만).

    gts   : [(cls, x, y, w, h), ...]
    preds : [(cls, conf, x, y, w, h), ...]
    돌려주는 값:
        tp        같은 Class · IoU ≥ 기준 으로 짝지어진 예측 수
        fp        짝이 없는 예측 수 (class_err 포함)
        fn        짝이 없는 GT 수 (놓친 것)
        class_err fp 중에서 위치는 맞는데(IoU ≥ 기준) Class 만 틀린 예측 수
        fn_idx    놓친 GT 의 번호 목록
        fp_cls    짝이 없는 예측의 Class 목록 (Class별 FP 집계용)
    """
    used, tp, class_err, fp_cls = set(), 0, 0, []
    for p in sorted(preds, key=lambda p: -p[1]):
        best_i, best_iou = None, iou_thr
        for i, g in enumerate(gts):
            if i in used or g[0] != p[0]:
                continue
            v = iou_xywh(g[1:], p[2:])
            if v >= best_iou:
                best_i, best_iou = i, v
        if best_i is not None:
            used.add(best_i)
            tp += 1
            continue
        fp_cls.append(p[0])
        if any(iou_xywh(g[1:], p[2:]) >= iou_thr for i, g in enumerate(gts) if i not in used and g[0] != p[0]):
            class_err += 1
    fn_idx = [i for i in range(len(gts)) if i not in used]
    return {"tp": tp, "fp": len(fp_cls), "fn": len(fn_idx), "class_err": class_err, "fn_idx": fn_idx, "fp_cls": fp_cls}
