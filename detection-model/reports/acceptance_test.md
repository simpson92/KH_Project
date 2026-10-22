# Acceptance Test (인계 단계 · 산출물 7)

> **상태: ACCEPTED** (2026-10-15 · 확인자 최용훈 · 33 / 33 PASS · FAIL 0)
> Final 선정 단계 완료 시점에 저장소 · 실행 기록으로 25개를 먼저 확인하고, 나머지 8개는 학습 PC 에서 직접 확인했다.
> 확인 기준: main 브랜치 (Final 선정 단계 완료 · PR #114) · Dataset `kimchi_v1` · Final Model `models/final/final_best.pt` (sha `029c0e92e594`)

## 1. Dataset

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| D1 | 검수 완료 데이터셋 데이터의 출처를 확인할 수 있다 | PASS | README 2 · 3장 (JPG 900 · TXT 900 · source_dataset 3묶음) · `reports/audit_check.csv` (19/19) |
| D2 | Dataset Version 을 확인할 수 있다 | PASS | `kimchi_v1` · 라벨 지문 `5c2b4fc2c3e6` (5명 일치 · README 4장) |
| D3 | `source_dataset / original_split / scene_type` 을 추적할 수 있다 | PASS | `manifests/*.csv` v2 9칸 (`reports/manifest_schema_check.csv` 14/14) |
| D4 | Train / Validation / Frozen Test / Bridge Holdout Manifest 가 존재한다 | PASS | `manifests/` train 600 · val 74 · test 80 · bridge_holdout 146 · split_manifest 900 |
| D5 | Split 정책을 설명할 수 있다 | PASS | `docs/split_policy.md` (5분 촬영 세션 · 예외 E1 · 합격 기준 8/8 · Leakage 근거) |
| D6 | Frozen Test 가 Final Model 선택 전에 사용되지 않았다 | PASS | `final_model_selection.md` 커밋 `a322016` (10/15 10:20) → Test 실행 10:22 (`reports/final_test_runs.csv`) · 10 · 14 는 test 코드 없음 · 11 · 15 는 val 만 허용 |
| D7 | Bridge Holdout 이 검출 모델 단계 학습 · 튜닝 · 모델 선택 · Frozen Test 에 사용되지 않았다 | PASS | `configs/dataset.yaml` 에 Bridge 없음 · 08 이 data/yolo 로 복사하지 않음 · 17 이 Test 외 사진 거부 · 모든 스크립트 검사 "Bridge 없음" PASS |

## 2. Model

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| M1 | Baseline Model 과 Final Model 을 구분할 수 있다 | PASS | baseline_v1 (imgsz 640 · sha `22f35d20a5ea`) · Final = exp001 (imgsz 1280 · sha `029c0e92e594`) · `reports/experiment_log.csv` |
| M2 | Baseline 학습조건이 기록되어 있다 | PASS | `configs/baseline.yaml` · `reports/baseline_training_condition.md` |
| M3 | `baseline_best.pt` 가 있다 | PASS | 학습 PC `models/baseline/baseline_best.pt` · sha `22f35d20a5ea` = Baseline 학습 단계 기록 (10/15 확인 · Git 제외) |
| M4 | `final_best.pt` 가 있다 | PASS | 학습 PC `models/final/final_best.pt` · sha `029c0e92e594` (10/15 재확인 · 16 · 17 검사도 PASS) |
| M5 | Final Model 을 선택한 이유가 기록되어 있다 | PASS | `reports/final_model_selection.md` (Val 비교 · 대표 FP/FN · 이유 4가지 · 원본 Weight) |

## 3. Evaluation

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| E1 | Baseline Validation 결과가 있다 | PASS | `reports/baseline_metrics.csv` · `baseline_class_check.csv` · `baseline_val_image_check.csv` |
| E2 | Precision 을 확인할 수 있다 | PASS | Val 0.655 → 0.729 (exp001) · Test 0.844 (conf 0.25 기준은 `*_class_check.csv`) |
| E3 | Recall 을 확인할 수 있다 | PASS | Val 0.595 → 0.732 · Test 0.560 · conf 0.25: 0.591 → 0.846 → Test 0.683 |
| E4 | mAP50 을 확인할 수 있다 | PASS | Val 0.622 → 0.756 · Test 0.606 |
| E5 | mAP50-95 를 확인할 수 있다 | PASS | Val 0.462 → 0.641 · Test 0.478 |
| E6 | Failure Analysis 가 있다 | PASS | `reports/failure_analysis.csv` (17행) · `failure_hypothesis.md` (확정) |
| E7 | Baseline vs Improved 비교 결과가 있다 | PASS | `reports/baseline_vs_improved.md` · `experiment_log.csv` |
| E8 | Frozen Test 결과가 있다 | PASS | `reports/final_metrics.csv` · `final_class_check.csv` · `figures/final_test_*.png` |

## 4. Inference

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| I1 | 이미지 Detection 이 실행된다 | PASS | `scripts/17_auto_label.py` → `demo/prediction_images/` 8장 (김하민 · 심준형 · 박건 PC 에서 실행) |
| I2 | BBox 가 표시된다 | PASS | 학습 PC 에서 17 실행 → `demo/prediction_images/` 그림을 열어 확인 (10/15) |
| I3 | Class 가 표시된다 | PASS | 위와 같음 — 박스 위 Class 이름 |
| I4 | Confidence 가 표시된다 | PASS | 위와 같음 — Class 옆 확신도 숫자 |

## 5. Auto Label

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| A1 | 새 이미지에서 후보 라벨을 만들 수 있다 | PASS | Test 8장(새 사진 없음) → 후보 43개 · `reports/auto_label_candidates.csv` |
| A2 | YOLO TXT 후보가 저장된다 | PASS | `demo/auto_label/candidate_labels/*.txt` 8개 (Git 제외) |
| A3 | 라벨 검수 도구에서 다시 열 수 있다 | PASS | 라벨 검수 도구 v4.1 로 `review_workspace` 열어 3명 검수 |
| A4 | 사람이 수정 · 삭제 · 추가할 수 있다 | PASS | 공식(심준형): Class 수정 2 · BBox 수정 3 · 삭제 7 · 추가 7 · `reports/auto_label_review.csv` |
| A5 | 승인된 라벨을 저장할 수 있다 | PASS | `demo/auto_label/reviewed_labels/*.txt` 8개 (Git 제외) · 승인 31 |

## 6. 인계 단계 추가 확인

| # | 항목 | 결과 | 방법 |
|---|---|---|---|
| X1 | Feature Freeze (새 기능 · 실험 없음) | PASS | 10/15 팀 공지 · 이후 문서 · 오탈자만 · Git 태그 `subject8_final_v1` |
| X2 | 외부 Git 에 사진 · 라벨 · weight · runs 없음 | PASS | `git ls-files \| grep -iE '\.(jpe?g\|pt\|onnx\|engine)$\|/runs/\|/data/\|/models/'` → 출력 없음 (10/15) |
| X3 | 다른 팀원이 README 만 보고 핵심 기능을 실행 | PASS | 김하민 · 심준형 · 박건이 각자 PC 에서 README 6장 23~25 순서(17 → 라벨 검수 단계 검수 → 18)로 실행 · 학습 PC 재실행도 같은 8장 · 후보 43개 (재현) |
| X4 | `git status` 최종 확인 | PASS | `working tree clean` (10/15) |

## 7. FAIL · Retest 기록

| 날짜 | 항목 | FAIL 내용 | 수정 | Retest |
|---|---|---|---|---|
| 10/15 | — | 없음 (Acceptance 중 FAIL 0) | — | — |

## 8. 판정

- **ACCEPTED** — PASS 33 / 33 · FAIL 0 · 확인자 최용훈 · 2026-10-15
- 참고 (개발 중 고친 것 · Acceptance FAIL 아님): 13 비교 그림이 정답을 가림 → 정답 박스 pad · MISSED 노랑 / 14 계획서 확정 검사가 초안 문구로 통과 → 굵은 머리줄만 인정

## 9. Final Gate 자가점검 (발표 전)

| 구분 | 항목 | 결과 · 근거 |
|---|---|---|
| 라벨 검수 단계 연결 | FINAL 데이터 · JPG 900 + TXT 900 · Class 0~6 유지 · source/original_split/scene_type 보존 · 라벨 검수 단계 QA 확인 | ✅ D1 · D3 · README 2 · 4장 · labeling-qa-tool/reports/qa_summary.md |
| Dataset | Audit · Split Policy 문서 · Leakage 확인 · 4역할 Freeze · bridge_holdout.csv 있고 dataset.yaml 에 없음 · Version 확인 | ✅ audit_check 19/19 · split_policy.md 3장 · freeze_check 13/13 · D7 |
| 학습 | Smoke Test · Baseline Model · Baseline 조건 · Improved 실험 · 실패 · 나빠진 결과도 기록 | ✅ smoke_test.md · M2 · M3 · experiment_log.csv · baseline_vs_improved.md (갈변 · 비용 증가 기록) · 실험은 exp001 1개 |
| 평가 | P · R · mAP50 · mAP50-95 · Class별 · 대표 FP/FN · 실패 원인 가설 | ✅ E1~E8 · failure_hypothesis.md |
| Final Model | Test 전에 선택 · final_best.pt · Frozen Test 결과 · 반복 튜닝 없음 | ✅ D6 · M4 · E8 · final_test_runs.csv (1회) |
| 활용 | Detection · Auto Label 후보 · Human Review | ✅ I1~I4 · A1~A5 |
| 문서 | README · acceptance_test.md · handoff_subject14.md · failure_analysis · failure_hypothesis · experiment_log · baseline_vs_improved · final_metrics | ✅ 모두 main 에 있음 |
| 보안 | 기업 Dataset · 원본 이미지 · YOLO TXT 원본 · *.pt/onnx/engine · runs/ · Prediction 이미지가 Git 에 없음 · .gitignore 적용 · git status | ✅ X2 · X4 · 최상위 .gitignore (detection-model/models · demo · **/*.jpg 등) |
| 산출물 8 (발표) | final_presentation.pdf · 시연 2개 · qna_guide.md | ⏳ 발표 준비 주간 (자료: 발표 자료 모음 v2) |
