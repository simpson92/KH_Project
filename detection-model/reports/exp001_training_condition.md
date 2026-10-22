# exp001 학습 조건 (산출물 4)

> **상태**: 완료  ·  **작성**: `scripts/14_train_experiment.py` 자동 생성  ·  **조건 원본**: `configs/exp001.yaml`
> 비교 기준: `baseline_v1` (`configs/baseline.yaml`) · 계획: `reports/improvement_experiment.md`

## 1. 바꾼 것 (한 변수)

| 설정 | Baseline | 이번 실험 |
|---|---|---|
| **imgsz** | 640 | **1280** |

그 밖의 학습 설정(epochs, patience, batch, workers, optimizer, lr0, momentum, seed, deterministic, amp, pretrained, model)은 Baseline 과 같다.
Dataset Version `kimchi_v1` · 라벨 지문 `5c2b4fc2c3e6` · Train 600 / Val 74 (Baseline 과 같음)

환경: NVIDIA GeForce RTX 3060 · Ultralytics 8.4.175 · PyTorch 2.14.1+cu130 · Python 3.10.12 · 코드 `77aef72`

## 2. 학습 전 검사

| 결과 | 항목 | 기대 | 실제 |
|---|---|---|---|
| PASS | Ultralytics 버전 (팀 고정) | 8.4.175 | 8.4.175 |
| PASS | CUDA (GPU 학습) | True | True |
| PASS | dataset.yaml Class 수 | 7 | 7 |
| PASS | dataset.yaml 에 Bridge 없음 | no | no |
| PASS | manifest 스키마 | v2 | v2 |
| PASS | Dataset Version = Baseline | kimchi_v1 | kimchi_v1 |
| PASS | 라벨 지문 | 5c2b4fc2c3e6 | 5c2b4fc2c3e6 |
| PASS | 09 data/yolo 검증 | 종료 코드 0 | 종료 코드 0 · → PASS 19 / FAIL 0   (저장: reports/yolo_verify_check.csv) |
| PASS | 시작 가중치 있음 | yolo11n.pt | yolo11n.pt |
| PASS | Baseline 과 다른 학습 설정 = 정확히 1개 | 1개 | imgsz 640 → 1280 |
| PASS | improvement_experiment.md 확정 · 변수 기록 | **상태: 확정** · `imgsz` · 1280 | 확정 |
| PASS | runs/exp001 아직 없음 (덮어쓰기 방지) | 없음 | 없음 |
| PASS | models/improved/exp001_best.pt 아직 없음 | 없음 | 없음 |
| PASS | configs · src · scripts · manifests 커밋됨 | 변경 없음 | 변경 없음 |

## 3. 실행 기록

| 항목 | 값 |
|---|---|
| 학습 시작 · 종료 | 2026-10-15 08:29 → 2026-10-15 08:47 (18.8분) |
| 완료 epoch | 50 / 50 |
| loss NaN · inf | 0개 |
| GPU 메모리 최대 (reserved) | 10.14 GB / 12 GB |
| 결과 폴더 | `runs/exp001/` (Git 제외) |
| Improved Weight | `models/improved/exp001_best.pt` · sha `029c0e92e594` (= `runs/exp001/weights/best.pt`) |
| results.csv | 사본 `reports/exp001_results.csv` |

> 평가는 `scripts/15_evaluate_experiment.py` (Baseline 과 같은 Val · 같은 채점 코드).
