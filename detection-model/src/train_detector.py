"""YOLO 학습 공통 기능 (17.2 src/train_detector.py).

Baseline(10_train_baseline.py)과 개선 실험이 같은 함수를 쓴다.
→ 두 실험의 차이는 "넘겨 준 설정값" 하나뿐이어야 한다 (한 번에 한 변수).

여기서는 학습만 한다. 학습 전 검사 · 결과 정리 · 기록은 실행 스크립트(scripts/)가 맡는다.
"""
from pathlib import Path

# Ultralytics model.train() 에 그대로 넘기는 설정 키 (configs/baseline.yaml 과 같은 이름)
TRAIN_KEYS = ["epochs", "patience", "imgsz", "batch", "workers", "optimizer", "lr0",
              "momentum", "seed", "deterministic", "amp", "pretrained"]


def train_detector(model_path: str, data_yaml: str, cfg: dict, project: Path, name: str) -> Path:
    """YOLO 모델을 학습하고 결과 폴더(save_dir)를 돌려준다.

    Args:
        model_path: 시작 가중치 (예: detection-model/yolo11n.pt)
        data_yaml:  configs/dataset.yaml (train · val 만 학습에 사용 · test 는 쓰지 않음)
        cfg:        학습 설정 dict (TRAIN_KEYS 만 사용)
        project:    결과 상위 폴더 · 반드시 절대경로 (상대경로면 Ultralytics 가 runs_dir 밑에 만듦)
        name:       결과 폴더 이름 (예: baseline_v1 → project/baseline_v1)

    Returns:
        실제 결과 폴더 Path (weights/best.pt · results.csv 가 있는 곳)
    """
    from ultralytics import YOLO                     # 함수 안에서 import → 검사만 할 때(--dry-run)는 불필요

    if not Path(project).is_absolute():
        raise ValueError(f"project 는 절대경로여야 합니다: {project}")

    args = {k: cfg[k] for k in TRAIN_KEYS if k in cfg}
    model = YOLO(model_path)
    model.train(
        data=data_yaml,
        project=str(project),
        name=name,
        exist_ok=False,          # 같은 이름 폴더가 있으면 Ultralytics 는 baseline_v12 처럼 번호를 붙임
                                 # → 실행 스크립트가 학습 전에 "폴더 없음"을 확인하고, 학습 후 이름을 다시 확인
        **args,
    )
    return Path(model.trainer.save_dir)              # Ultralytics 가 실제로 저장한 위치
