# Baseline 학습 조건 (산출물 2)

> **상태**: 완료  ·  **작성**: `scripts/10_train_baseline.py` 자동 생성  ·  **조건 원본**: `configs/baseline.yaml`
> 성능 해석은 Baseline 평가 단계 `reports/baseline_metrics.csv` 에서 한다. 이 문서는 '어떤 조건으로 학습했는가'만 기록한다.

## 1. 학습 조건 (Freeze)

| 항목 | 값 |
|---|---|
| Model | YOLO11n (`yolo11n.pt` · pretrained=True) |
| Dataset Version | `kimchi_v1` · 라벨 지문 `5c2b4fc2c3e6` |
| Train / Val Manifest | 스키마 v2 · Train 600장 (`train.csv` sha `73415d994d4d`) · Val 74장 (`val.csv` sha `df2fb1b6aefa`) |
| Epoch · Patience | 50 · 50 |
| Batch | 16 |
| Image Size | 640 |
| Seed · Deterministic | 42 · True |
| Optimizer · Learning Rate · Momentum | AdamW · 0.000909 · 0.9 (auto 대신 명시 고정) |
| AMP · Workers | True · 2 |
| GPU | NVIDIA GeForce RTX 3060 (CUDA True) |
| Ultralytics · PyTorch · Python | 8.4.175 · 2.14.1+cu130 · 3.10.12 |
| 코드 버전 (git commit) | `c12bf76` |

## 2. 학습 전 검사

| 결과 | 항목 | 기대 | 실제 |
|---|---|---|---|
| PASS | Ultralytics 버전 (팀 고정) | 8.4.175 | 8.4.175 |
| PASS | CUDA (GPU 학습) | True | True |
| PASS | dataset.yaml Class 수 | 7 | 7 |
| PASS | dataset.yaml 에 Bridge 없음 | no | no |
| PASS | manifest 스키마 | v2 | v2 |
| PASS | Dataset Version | kimchi_v1 | kimchi_v1 |
| PASS | 라벨 지문 | 5c2b4fc2c3e6 | 5c2b4fc2c3e6 |
| PASS | 09 data/yolo 검증 | 종료 코드 0 | 종료 코드 0 · → PASS 19 / FAIL 0   (저장: reports/yolo_verify_check.csv) |
| PASS | 시작 가중치 있음 | yolo11n.pt | yolo11n.pt |
| PASS | runs/baseline_v1 아직 없음 (덮어쓰기 방지) | 없음 | 없음 |
| PASS | models/baseline/baseline_best.pt 아직 없음 | 없음 | 없음 |
| PASS | configs · src · scripts · manifests 커밋됨 | 변경 없음 | 변경 없음 |

## 3. 실행 기록

| 항목 | 값 |
|---|---|
| 학습 시작 · 종료 | 2026-10-14 10:18 → 2026-10-14 10:32 (13.9분) |
| 완료 epoch | 50 / 50 |
| loss NaN · inf | 0개 (6개 loss 칸 검사) |
| 결과 폴더 | `runs/baseline_v1/` (Git 제외) |
| Baseline Weight | `models/baseline/baseline_best.pt` · sha `22f35d20a5ea` (= `runs/baseline_v1/weights/best.pt`) |
| results.csv | `runs/baseline_v1/results.csv` · 사본 `reports/baseline_results.csv` |

## 4. Baseline 학습 단계 Daily Gate

- ✅ 전체 Train Dataset(600장)으로 Baseline 학습이 완료되었습니다.
- ✅ `reports/baseline_training_condition.md`에 실제 학습조건을 기록했습니다. (이 문서)
- ✅ `models/baseline/baseline_best.pt`가 별도 보관되었습니다.
- ✅ `runs/baseline_v1/results.csv`를 보존했습니다. (사본 `reports/baseline_results.csv`)
- ✅ Dataset Version을 확인할 수 있습니다. (`kimchi_v1` · 라벨 지문 · manifest sha)
- ✅ Frozen Test와 Bridge Holdout을 사용하지 않았습니다. (dataset.yaml 에 Bridge 없음 · test 평가 코드 없음 · Test 지문 `4f9291849fe6` 기록만)

> `reports/baseline_metrics.csv`는 Validation 평가 후 작성합니다.
