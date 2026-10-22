# Final Model 선택 (Final 선정 단계 · 산출물 4)

> **상태: 확정** (2026-10-15 · Frozen Test 를 보기 전 · Validation 결과만으로 결정)
> 근거: `reports/baseline_vs_improved.md` (4장) · `reports/experiment_log.csv` · `reports/failure_hypothesis.md` (H1)
> 이 문서를 **커밋한 뒤에만** `scripts/16_evaluate_final_test.py` 가 Frozen Test 를 연다 (선택 → 시험 순서를 Git 기록으로 남김).

## 1. Final Model

| 항목 | 값 |
|---|---|
| Final Weight | `models/final/final_best.pt` · sha `029c0e92e594` |
| 원본 Weight | `models/improved/exp001_best.pt` · sha `029c0e92e594` (= `runs/exp001/weights/best.pt`) |
| 원본 실험 | exp001 — Baseline 에서 **imgsz 640 → 1280** 하나만 변경 (실패 분석 단계 H1 작은 이물 놓침) |
| 원본 설정 | `configs/exp001.yaml` (imgsz 1280) |
| 학습 | 2026-10-15 08:29 → 08:47 · 50/50 epoch · loss NaN 0 · GPU 최대 10.14 GB · 코드 `77aef72` |
| Dataset | `kimchi_v1` · 라벨 지문 `5c2b4fc2c3e6` · Train 600 / Val 74 |
| 후보 | baseline_v1 (sha `22f35d20a5ea` · imgsz 640) / **exp001 (sha `029c0e92e594` · imgsz 1280)** |

> Git 에는 weight 를 올리지 않는다 (`models/` 제외 · NDA). 같은 파일인지는 sha 로 확인한다.

## 2. 같은 Validation 비교 (Val 74장 · 정답 389개 · 같은 채점 코드)

| 지표 | baseline_v1 | exp001 | 변화 |
|---|---|---|---|
| P · R (Ultralytics) | 0.655 · 0.595 | 0.729 · 0.732 | ▲ · ▲ |
| mAP50 | 0.622 | **0.756** | +0.134 |
| mAP50-95 | 0.462 | **0.641** | +0.179 |
| Recall (conf 0.25) | 0.591 | **0.846** | +0.254 |
| FN 놓침 (conf 0.25) | 159 | **60** | −99 |
| FP 오검출 (conf 0.25) | 92 | **41** | −51 |
| 작은 객체 FN (/363 · 640 기준 32px) | 153 | **57** | −96 |

## 3. 대표 FP / FN 변화

- **H1 작은 이물 놓침 → 크게 개선**: 작은 객체 FN 153 → 57 · 플라스틱 FN 147 → 52 · 실패 분석 단계 대표 사진 14장 FN 49 → 25 (14장 모두 같거나 감소)
- **H3 branch 오검출 → 거의 해결**: branch FP 30 → 1 · 벌레 FP 14 → 1
- **H2 갈변 → 그대로**: 갈변 FN 6 → 6 · FP 13 → 15 (Final Model 의 알려진 약점)
- 나빠진 것: 갈변 FP +2 · 파 · 고추 FP +1 (표본 6개) · 학습 시간 13.9 → 18.8분 · GPU 메모리 2.48 → 10.14 GB · 사진 1장 처리 약 15 → 17 ms

## 4. 선택 이유

1. 실패 분석 단계 반복 문제 H1 이 가설대로 줄었다 (작은 객체 FN −63%).
2. 주요 지표가 모두 Val 74장의 잡음 범위(0.01~0.03)보다 크게 좋아졌다.
3. FN 과 FP 가 **함께** 줄었다 → conf 기준을 바꾼 효과가 아니라 모델이 실제로 더 잘 본다.
4. 갈변은 두 모델 모두 0개 검출이라 exp001 을 고르지 않을 이유가 되지 않는다.

## 5. Frozen Test 평가 조건 (선택 후 1회만)

| 항목 | 값 | 이유 |
|---|---|---|
| 평가 대상 | `data/yolo/images/test` 80장 · Test 지문 `4f9291849fe6` | Split 단계에 봉인한 Frozen Test |
| imgsz | **1280** | Final Model 이 학습한 크기와 같게 (예시 코드의 640 은 "Final Model 평가조건과 일치" 를 뜻함 · 640 으로 평가하면 작은 이물이 다시 작아져 실제 성능보다 낮게 나옴) |
| conf · IoU (이미지별 · Class별 표) | 0.25 · 0.5 | Val 과 같은 채점 기준 (11 의 함수) |
| 횟수 | **1회** | Test 결과를 보고 다시 고르거나 튜닝하지 않는다 · 16 이 두 번째 실행을 막는다 |
| Bridge Holdout | 사용 안 함 | 후속 프로젝트 보존 |

> Frozen Test 결과가 Val 보다 낮게 나와도 Final Model 을 바꾸지 않고 그대로 기록한다 (`reports/final_metrics.csv` · README 14장).
