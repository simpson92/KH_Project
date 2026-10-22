# 후속 프로젝트 인계 문서 (검출 모델 → 후속 프로젝트 · 산출물 7)

> **상태**: 확정 (2026-10-15 · 인계 단계 · Acceptance ACCEPTED · Feature Freeze 후)
> 목적: 후속 제조 제품검사 프로젝트가 **다시 처음부터 조사하지 않도록** 검출 모델 단계 의 데이터 · 모델 · 성능 · 약점 · 남은 일을 넘긴다.
> 후속 프로젝트 의 첫 연결점: **Bridge Holdout 146장으로 검출 모델 단계 Final Model 을 다시 확인하는 것**

## 1. Dataset

| 항목 | 값 |
|---|---|
| Dataset Version | `kimchi_v1` (검수 완료 데이터셋 10/08 수정본 · BBox 4,601) |
| 라벨 지문 | `5c2b4fc2c3e6` (`data/subject7_final/labels` sha256 앞 12자리 · 5명 일치) |
| Class | 0 leaf_paper · 1 plastic_stone_metal · 2 branch · 3 insect · 4 rubber_glove (미사용 · 0건) · 5 disease_browning · 6 green_onion_pepper (라벨 검수 단계 번호 그대로) |
| Split 단위 | 5분 촬영 세션(capture_group) · 한 세션은 한 역할에만 · 예외 E1 (G01 만 2분 하위 세션) · `docs/split_policy.md` |

| 역할 | 사진 | BBox | Class 0 · 1 · 2 · 3 · 5 · 6 | 촬영 날짜 | 검출 모델 단계 사용 |
|---|---:|---:|---|---|---|
| Train | 600 | 2,957 | 727 · 764 · 551 · 322 · 391 · 202 | 4/10 · 4/11 · 4/24 · 5/13 | 학습 |
| Val | 74 | 389 | 7 · 351 · 8 · 11 · 6 · 6 | 4/10 · 4/11 | 비교 · 선택 |
| Frozen Test | 80 | 477 | 143 · 147 · 122 · 24 · 21 · 20 | 4/10 · 4/11 · 4/24 | Final 확정 후 1회 |
| **Bridge Holdout** | **146** | **778** | **47 · 635 · 30 · 21 · 21 · 24** | 4/10 · 4/11 · 4/24 | **사용 안 함** |

## 2. Bridge Holdout (후속 프로젝트 의 첫 시험지)

| 항목 | 값 |
|---|---|
| 목록 | `manifests/bridge_holdout.csv` (146행 · v2 9칸) |
| 사진 · 라벨 위치 | `data/subject7_final/images · labels` 안 (목록의 `image_path` · `label_path`) · `data/yolo` 로 복사하지 않음 · Git 제외 |
| 세션 | G07 76 · G04 39 · G12 25 · G01-S3 5 · G02 1 |
| 파일명 지문 | `fd6c14c2ac0a` (`src/manifest.fingerprint` 와 같은 계산 · 파일명 146개를 정렬해 sha256 앞 12자리 · 후속 프로젝트 시작 시 같은 값인지 먼저 확인) |
| 검출 모델 단계 미사용 확인 | `configs/dataset.yaml` 에 없음 · 08 이 복사하지 않음 · 평가 함수가 `bridge_holdout` 을 막음 · 16 · 17 이 Test 외 사진 거부 · Acceptance D7 |
| 주의 | Class 1(플라스틱)이 82% (635/778) — Bridge 점수도 플라스틱 위주가 됨 → Class 별로 함께 볼 것 |

## 3. Final Model

| 항목 | 값 |
|---|---|
| Weight | `models/final/final_best.pt` · sha `029c0e92e594` (= `models/improved/exp001_best.pt` · Git 제외 · 이동은 기관이 허락한 방법으로만) |
| 모델 · 조건 | YOLO11n · **imgsz 1280** · epochs 50 · batch 16 · AdamW 0.000909 · momentum 0.9 · seed 42 (`configs/exp001.yaml`) |
| Baseline 과 차이 | imgsz 640 → 1280 하나 (실패 분석 단계 H1 작은 이물 놓침) |
| 환경 | Ultralytics 8.4.175 · PyTorch 2.14.1+cu130 · Python 3.10.12 · RTX 3060 12GB · WSL |
| 학습 비용 | 18.8분 · GPU 최대 10.14 GB · 추론 약 4.5 + 6.9 + 3.5 ms/장 (전처리 · 추론 · 후처리 · Test) |
| 선택 근거 | `reports/final_model_selection.md` · `reports/baseline_vs_improved.md` |
| **평가 · 사용 시 imgsz** | **1280** (640 으로 쓰면 작은 이물이 다시 작아져 성능이 떨어짐) |

## 4. 성능 (Val 은 선택용 · Frozen Test 는 1회)

| 지표 | Val 74장 | Frozen Test 80장 |
|---|---|---|
| P · R (Ultralytics) | 0.729 · 0.732 | 0.844 · 0.560 |
| mAP50 · mAP50-95 | 0.756 · 0.641 | **0.606 · 0.478** |
| Recall · Precision (conf 0.25) | 0.846 · 0.889 | 0.683 · 0.660 |
| 정답 · FN · FP (conf 0.25) | 389 · 60 · 41 | 477 · 151 · 168 |

Class 별 Frozen Test (conf 0.25 · Recall / mAP50): leaf 0.77 / 0.565 · plastic 0.73 / 0.809 · branch 0.58 / 0.649 · insect 0.92 / 0.898 · browning 0.14 / 0.049 · onion 0.60 / 0.670

## 5. 잘하는 상황 · 약한 상황

| 잘함 | 근거 |
|---|---|
| 모양이 뚜렷한 벌레 | Test Recall 0.92 · mAP50 0.898 |
| 플라스틱 (Val 세션) | Val Recall 0.85 · imgsz 1280 으로 작은 플라스틱 놓침 147 → 52 |
| 김치 줄기 · 그림자를 가지로 착각하는 오검출 | Val branch FP 30 → 1 |

| 약함 | 근거 | 후속 프로젝트 에서 |
|---|---|---|
| **나뭇잎 ↔ 나뭇가지 혼동** | Test Confusion Matrix: branch 의 39% → leaf · leaf 의 29% → branch · plastic 의 27% → leaf | 두 Class 기준(라벨 검수 단계 class_guide) 재확인 · 라벨 검수 단계 에서도 10/08 에 2 → 0 56개 수정 이력 |
| **갈변 (disease_browning)** | Val 0/6 · Test 3/21 · 갈변 43% 를 배경으로 놓침 · 정답 없는 자리 오검출의 54% 가 갈변 | 갈변 데이터 · 라벨 기준 · 색 관련 실험 |
| **새 촬영 세션 (4/24 · G11)** | Test G11 50장에 FN 102/151 (68%) · FP 136/168 (81%) · Val 에는 4/24 사진 없음 | Bridge(4/24 포함)로 재확인 · 세션 다양한 검증 세트 |
| 작은 객체 (새 세션) | Test 작은 객체 놓침 124/315 (39%) · Val 57/363 (16%) | 해상도 · 타일링 등 (후속 프로젝트 에서 장치 비용과 함께) |
| 정상 김치 | 0장 → 정상 김치 오검출을 잴 수 없음 | Negative 사진 확보 |

## 6. 대표 FP / FN (Frozen Test · `reports/final_test_image_check.csv`)

- FN · FP 가 가장 많은 사진: `250411_134515221630` (G08 · FN 6 · FP 5) · `250424_112256216378` (G11 · FN 7 · FP 4) · `250424_111020116028` (G11 · FN 5 · FP 5 · Class 오류 4) · `250424_113017660157` (G11 · FN 5 · FP 5 · Class 오류 4)
- 80장 중 73장에 FN 또는 FP 가 1개 이상 · 세션별 Recall(conf 0.25): G08 0.73 · G11 0.67
- 실패 분석 단계 Val 대표 실패 사례: `reports/failure_analysis.csv` (17행) · 비교 그림은 `demo/failure_analysis/` (Git 제외)

## 7. 라벨 이슈 (kimchi_v1 에서 고치지 않고 넘김)

| 사진 (Val) | 문제 | 상태 |
|---|---|---|
| `250411_140005265446` | plastic 정답 박스 2개가 빈 자리 (트레이 상단 · 4K 13×17 · 12×13px) | 라벨 오류 · 사람 확인 |
| `250411_092158458691` | 정답 없는 자리에 갈변으로 보이는 이물 (Class 5 누락 후보) | 누락 후보 |
| `250411_094548003041` | 정답 없는 자리에 돌로 보이는 이물 (Class 1 누락 후보) | 누락 후보 |

→ 고치면 `kimchi_v2` 로 버전을 올리고 Baseline · Final 을 같은 v2 로 다시 평가해야 함. 근거: `reports/issue_log.md` 10/14 · 10/15

## 8. Detection · Auto Label 결과 위치

| 무엇 | 위치 | Git |
|---|---|---|
| Detection 그림 (Test 8장) | `demo/prediction_images/` | ❌ |
| AI 후보 · 사람 검수 라벨 | `demo/auto_label/candidate_labels/` · `reviewed_labels/` | ❌ |
| 검수 집계 (공식 · 심준형) | `reports/auto_label_review.csv` — 후보 43 · 승인 31 (72%) · Class 수정 2 · BBox 수정 3 · 삭제 7 · 추가 7 | ✅ |
| 검수자 3명 범위 | 승인 70~74% · BBox 수정 1~7 · 추가 3~7 · 정답 일치 76~78% (README 15장) | ✅ |
| 재실행 | `python scripts/17_auto_label.py` → 라벨 검수 도구으로 `demo/auto_label/review_workspace` 열기 → `python scripts/18_auto_label_review.py` | — |

## 9. 후속 프로젝트 에서 이어갈 작업 (우선순위)

1. **Bridge Holdout 146장으로 Final Model 재확인** (imgsz 1280 · conf 0.25 · Class 별 · 세션 별) — 검출 모델 단계 결과(Test)와 비교
2. **검증 세트 다시 설계**: Val 에도 Class 별 최소 개수 · 촬영 날짜(4/24 포함) 반영 — 검출 모델 단계 Val 은 플라스틱 90% · 4/10 · 4/11 만
3. **나뭇잎 ↔ 나뭇가지 기준 재정리** (라벨 검수 단계 class_guide) → 필요하면 라벨 수정 → `kimchi_v2`
4. **갈변** 데이터 · 라벨 기준 점검
5. **정상 김치(Negative) 사진** 확보 → 오검출 측정
6. 라벨 이슈 3건(7장) 처리 → `kimchi_v2`
7. 현장 속도 · 장치 (imgsz 1280 · 약 15ms/장 · GPU 메모리) · 판정 로직
8. Auto Label 검수 기준 맞추기 (검수자 간 BBox 수정 1~7개 차이)

## 10. 재현 · 근거 문서

- 실행 순서: README 6장 (01 ~ 14) · 흐름: README 8장 · `docs/code_flow.md` · 코드 설명: `docs/code_review/` (scripts 01 ~ 14 · src 5개)
- 결정 기록: `docs/split_policy.md` · `reports/failure_hypothesis.md` · `reports/improvement_experiment.md` · `reports/final_model_selection.md` · `reports/issue_log.md`
- 실험 기록: `reports/experiment_log.csv` · `reports/final_test_runs.csv`
- 검수: `reports/acceptance_test.md`
