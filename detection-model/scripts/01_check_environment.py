"""환경 구성 단계: 개발 환경 확인 + YOLO 사전학습 모델 Load 확인."""
from pathlib import Path
import sys

# 이 파일 위치(scripts/)의 한 단계 위 = 프로젝트 루트(detection-model/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# scripts에서 src 기능을 import할 수 있도록 루트를 경로에 추가
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch
import ultralytics
from ultralytics import YOLO


def main():
    # 1. 주요 버전 확인 (팀원끼리 같아야 결과를 비교할 수 있음)
    print("Python      :", sys.version.split()[0])
    print("PyTorch     :", torch.__version__)
    print("Ultralytics :", ultralytics.__version__)

    # 2. GPU 확인 (False면 학습이 CPU로 돌아가서 매우 느려짐)
    print("CUDA 사용 가능:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("GPU         :", torch.cuda.get_device_name(0))

    # 3. YOLO11n 사전학습 모델 Load (처음 실행 시 자동 다운로드)
    model = YOLO("yolo11n.pt")

    # 사전학습 모델의 Class 수 출력 → 정상 Load 확인용
    # (COCO 80개가 나오는 게 정상, 우리 7개 Class는 학습 후에 적용됨)
    print("YOLO Load 성공, Class 수:", len(model.names))


if __name__ == "__main__":
    main()