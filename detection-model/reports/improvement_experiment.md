# 개선 실험 계획 — exp001 (개선 실험 단계 · 산출물 4)

> **상태: 확정** (2026-10-15 · 아침 회의 + 1 epoch 시험 결과로 확정 · 이 문서를 쓴 뒤 학습 시작)
> 근거: `reports/failure_hypothesis.md` (H1 · 5장 결정 규칙) · 설정: `configs/exp001.yaml` · 비교 기준: `baseline_v1`

## 1. 무엇을 바꾸나 (변수 하나)

| 변수 | Baseline | exp001 |
|---|---|---|
| `imgsz` (모델 입력 크기 · 긴 변) | 640 | **1280** |

## 2. 왜 바꾸나

- 실패 분석 단계 반복 문제 **H1 — 작은 이물 놓침**: 놓친 정답 159개 중 153개가 640 기준 32px 미만
  - 못 찾음 · 종류를 틀림(Class 혼동 7) · 몇 px 어긋남(위치 어긋남 8) 모두 "조각이 너무 작게 보인다"는 같은 뿌리
- 학습량 부족은 아님: Baseline 학습곡선이 30~40 epoch 에서 천장 → epochs 를 늘리는 대신 입력 크기를 키운다 ("Model / Training — 입력 크기")
- 기대: 640 에서 5~14px 이던 조각이 1280 에서 **2배(10~28px)** 로 보여 FN · Class 혼동 · 위치 어긋남이 함께 줄어든다

## 3. 무엇을 그대로 두나

Dataset Version `kimchi_v1` (10/15 회의 · 라벨 수정 안 함) · Train 600 / Val 74 · YOLO11n 사전학습 · epochs 50 · patience 50 · **batch 16** · AdamW 0.000909 · momentum 0.9 · seed 42 · deterministic · amp · workers 2 · 같은 학습 함수(`src/train_detector.py`) · 같은 채점 코드(11 의 함수를 15 가 그대로 사용)

→ `scripts/14_train_experiment.py` 가 학습 전에 "Baseline 과 다른 학습 설정 = 정확히 1개 (imgsz)" 를 검사한다.

## 4. 1 epoch 시험 결과 (`14_train_experiment.py --smoke` · 10/15 08:2x)

| 항목 | 값 |
|---|---|
| 조건 | imgsz 1280 · batch 16 · 1 epoch (runs/exp001_smoke · 기록용 아님) |
| 1 epoch 시간 | 학습 23.9초 + Val 5.3초 · 전체 약 0.7분 (Baseline 640: 약 0.3분) |
| 50 epoch 예상 | **약 25~34분** (Baseline 13.9분의 약 2~2.5배) |
| GPU 메모리 | 학습 표시 GPU_mem 9.29G · 최대 확보량 **9.97 GB / 12 GB** |
| Val 점수 | mAP50 0.003 (1 epoch · warmup 구간이라 의미 없음 · Split 단계 Smoke 와 같은 현상) |
| **결정** | 회의 규칙 "11GB 미만 → 1280" 에 따라 **imgsz 1280 확정** · batch 16 유지 |
| 주의 | 1 epoch 시험은 모자이크 증강이 꺼진 상태로 측정됨 (`Closing dataloader mosaic`) · 본 학습 1~40 epoch 는 모자이크가 켜져 메모리를 조금 더 쓸 수 있음 → 본 학습 중 메모리 부족(OOM)으로 멈추면 규칙대로 **imgsz 960 으로 바꿔 다시 학습** (`runs/exp001` 삭제 후 · issue_log 기록) |

## 5. 무엇을 보고 판단하나 (같은 Val 74장 · `15_evaluate_experiment.py`)

- 주 지표: **FN (conf 0.25 · Baseline 159) · 작은 객체 FN (Baseline 153 / 363) · Recall (conf 0.25 · Baseline 0.591)** — H1 이 실제로 줄었는가
- 함께 볼 것: mAP50 (0.622) · mAP50-95 (0.462) · FP 증가 여부 (92) · 갈변 FN (6 · H2) · branch FP (30 · H3) · 실패 분석 단계 대표 사진 14장의 FN 변화
- 판단 기준: Val 74장이라 0.01~0.03 차이는 잡음 범위 · **FN · 작은 객체 FN 의 뚜렷한 감소**를 개선으로 본다 · 나빠진 값도 함께 기록
- 결과가 나빠도 그대로 기록한다 (`experiment_log.csv` · `baseline_vs_improved.md`) · Final Model 후보는 Frozen Test 를 보지 않고 Validation 결과로만 정한다
