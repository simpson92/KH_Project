# Smoke Test 기록 (Split 단계)

> **구분**: 진행용 기록 · 최종 산출물 아님
> **목적**: `data/yolo` → YOLO11n 학습 → Prediction 까지 파이프라인이 끝까지 연결되는지 확인한다. **점수(mAP)는 평가하지 않는다.**
> **작성**: 2026-10-13 · 최용훈 (A PC) · B PC 결과는 5장 참고

## 1. 조건

| 항목 | 값 |
|---|---|
| Dataset Version | `kimchi_v1` · 라벨 지문 `5c2b4fc2c3e6` |
| 사용 데이터 | Train 600 · Val 74 (`manifests/` 기준 · `09` 검증 PASS 19 / FAIL 0) |
| **사용하지 않은 데이터** | **Frozen Test 80 · Bridge Holdout 146** (학습 · Prediction 모두 미사용) |
| 모델 | `yolo11n.pt` (사전학습 가중치) |
| 설정 | epochs=1 · imgsz=640 · batch=8 · workers=2 · seed=0 · deterministic=True (나머지 기본값) |
| 환경 | RTX 3060 12GB (CUDA:0) · Ultralytics 8.4.175 · PyTorch 2.14.1+cu130 · Python 3.10.12 |

## 2. 실행 명령

```bash
# 학습 (detection-model 에서)
yolo detect train model=yolo11n.pt data=configs/dataset.yaml epochs=1 imgsz=640 batch=8 workers=2 \
    project="$PWD/runs" name=smoke_day3 exist_ok=True

# Prediction ① conf 0.05 (Val 이미지 · Smoke Weight)
yolo detect predict model=runs/smoke_day3/weights/best.pt source=data/yolo/images/val conf=0.05 save=True \
    project="$PWD/runs" name=smoke_day3_predict exist_ok=True

# Prediction ② conf 0.25 (Ultralytics 기본값 · 보기 쉬운 비교용)
yolo detect predict model=runs/smoke_day3/weights/best.pt source=data/yolo/images/val conf=0.25 save=True \
    project="$PWD/runs" name=smoke_day3_predict_conf025 exist_ok=True
```

## 3. 결과

### 3.1 학습

| 확인 항목 | 결과 |
|---|---|
| GPU 사용 `CUDA:0 (NVIDIA GeForce RTX 3060, 12288MiB)` | ✅ |
| `Overriding model.yaml nc=80 with nc=7` (dataset.yaml 7 Class 반영) | ✅ |
| train Scanning 600/600 · `Using 600 train` · 경고 없음 | ✅ |
| val Scanning 74/74 · `74 val images` · 경고 없음 | ✅ |
| 1 epoch 완료 | ✅ 학습 18.0초 + 검증 3.1초 (`0.006 hours` ≈ 22초) |
| GPU_mem | 1.25G / 12G |
| Smoke Weight 생성 | ✅ `runs/smoke_day3/weights/best.pt` · `last.pt` (각 5.5MB) |
| 저장 위치 | `detection-model/runs/smoke_day3` (Git 제외) |
| (참고) Val 점수 | P 0.00003 · R 0.048 · mAP50 0.00001 → **평가하지 않음** (아래 4장 ①) |

### 3.2 Prediction

| 확인 항목 | 결과 |
|---|---|
| Prediction 실행 (Val 74장) | ✅ conf 0.05 · 0.25 두 번 모두 74/74장 처리 (conf 0.05 기준 이미지당 평균 15.7ms) |
| 저장 이미지에 BBox · Class · Confidence 표시 | ✅ 예: `plastic_stone_metal 0.90` · `leaf_paper 0.49` · `branch 0.40` |
| 저장 위치 | `runs/smoke_day3_predict/` · `runs/smoke_day3_predict_conf025/` (Git 제외 · NDA 이미지 · 외부 공유 금지) |

| conf | 이미지당 박스 수 | 모습 |
|---|---|---|
| 0.05 | 수십~140개 이상 · no detections 0장 | 박스가 겹겹이 쌓여 이미지를 거의 덮음 · 데이터에 0건인 Class 4 도 검출 |
| 0.25 | 수 개 수준으로 크게 감소 | 읽기는 쉬워졌지만 **여전히 부정확** · 예: 이미지 절반을 덮는 `plastic_stone_metal 0.90` 박스 · 같은 자리에 겹친 박스 |

> **conf 를 올리면 "보이는 박스 수"만 줄어든다. 모델 실력(위치 · 클래스 정확도)은 그대로다.** 실력은 학습(epochs)으로 올리며, Baseline 부터 평가한다.

## 4. 오류 · 경고와 해결

| # | 메시지 | 원인 | 조치 |
|---|---|---|---|
| ① | Val mAP50 ≈ 0 · `cls_loss 9.695` | 기본 `warmup_epochs=3` → 1 epoch 은 학습률을 올리는 준비 구간 안에서 끝남 | 정상 · Smoke Test 는 점수를 보지 않음 |
| ② | Prediction 박스가 이미지당 수십~140개 · 데이터에 0건인 Class 4(rubber_glove_unused)도 검출 | 1 epoch 모델이라 Class 점수가 거의 무작위 → conf 0.05 를 넘는 박스가 많음 (FP 대량) | conf 0.25 로 다시 실행 → 박스 수는 줄었지만 위치 · 클래스는 여전히 부정확 (높은 점수 0.90 박스도 오검출) · 정상 · 파이프라인 확인 목적 달성 |
| ③ | `optimizer: 'optimizer=auto' found, ignoring 'lr0=0.01'` → `AdamW(lr=0.000909)` | `optimizer=auto` 는 학습 길이에 따라 옵티마이저 · 학습률을 자동 선택 | **Baseline 에서 optimizer · lr0 를 직접 고정** (epochs 를 바꾸면 자동 선택도 바뀜) |
| ④ | `New https://pypi.org/project/ultralytics/8.4.176 available` | 새 버전 안내 | **업데이트하지 않음** · 팀 5명 8.4.175 고정 (환경 구성 단계 환경 표) |
| ⑤ | `Downloading … Arial.ttf` · `AMP: downloading yolo26n.pt` | 그림 글꼴 · AMP 점검용 1회 다운로드 | 정상 · yolo26n.pt 는 학습에 쓰이지 않음 (`not used for training`) |
| ⑥ | `data/yolo/labels/train.cache` · `val.cache` 생성 | Ultralytics 라벨 캐시 | 정상 · `data/` 는 Git 제외 |

> 실행을 멈추게 한 오류는 없었다.

## 5. 두 번째 PC (B) 결과

- B (pg 브랜치) PC 에서도 같은 설정으로 1 epoch 정상 종료 (PR #82 커밋 메시지)
- `data/yolo` 구성 결과는 A PC · B PC 가 완전히 같음 (`reports/yolo_build_summary.csv` diff 0 · Test 지문 `4f9291849fe6`)

## 6. 요구사항(§16.5 · §16.6)과 다른 점

| 요구사항 | 우리 팀 | 이유 |
|---|---|---|
| 작은 Smoke Dataset (Train 30~40 · Val 5~10장) · `data/smoke/` · `configs/smoke_dataset.yaml` | 전체 Train 600 · Val 74 · `configs/dataset.yaml` 그대로 · 1 epoch | 1 epoch 약 22초로 충분히 빠름 · 실제 학습 경로(`data/yolo`)를 그대로 검증해 Baseline 학습 단계와 같은 조건 확인 |
| `scripts/05_smoke_train.py` · `runs/smoke_v1` | `yolo detect train` CLI · `runs/smoke_day3` | 1회성 확인이라 스크립트 대신 명령 기록 (2장) |
| Prediction 1장 · conf 0.25 | Val 74장 · conf 0.05 / 0.25 비교 | 1 epoch 모델의 오검출 양상을 함께 확인 |

> Test · Bridge 미사용 · Smoke Weight ≠ Baseline 원칙은 요구사항 문서와 같다.

## 7. 주의 · 결론

- **Smoke Weight 는 Baseline 으로 사용하지 않는다.** (1 epoch · warmup 구간 · 점수 비교 대상 아님) Baseline 은 Baseline 학습 단계에 정한 설정으로 새로 학습한다.
- Frozen Test · Bridge Holdout 은 학습과 Prediction 어디에도 사용하지 않았다.
- Baseline 학습 단계 계획 근거: 1 epoch ≈ 22초 → 100 epoch ≈ 37분 · GPU_mem 1.25G 로 batch 를 올릴 여유가 있다.
- Baseline 학습 단계 결정 필요: optimizer · lr0 고정 (4장 ③) · batch 크기 · epochs
