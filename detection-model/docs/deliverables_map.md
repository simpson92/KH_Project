# 산출물 구분표 — 필수 산출물 vs 우리 산출물

> 기준: 과제 요구사항 문서 1장(최종 산출물 8가지) · 7장(권장 디렉토리) · 14~22장(단계별 Daily Gate)
> 대상: `detection-model/` main 브랜치 (Git에 올라간 파일 + Git 제외 파일은 README · 문서 기록 기준)

## 0. 읽는 법

| 구분 | 뜻 | 이 문서 위치 |
|---|---|---|
| **A. 필수 산출물** | 요구사항 문서가 산출물 1~8번으로 **파일 이름까지 지정**한 것 | 1장 |
| **B. 우리 산출물** | 요구사항 문서에 없는데 **우리 팀이 필요해서 만든 것** → 왜 만들었는지 설명 | 2장 |

> B의 대부분은 **"A가 맞다는 것을 증명하는 근거 파일"** 입니다.
> Git에서 제외한 파일(이미지 · 모델 · `runs/`)은 NDA 때문에 올릴 수 없어서, 그 안의 **숫자만** 따로 뽑아 Git에 남긴 것이 많습니다.

---

## 1. 필수 산출물 (A)

| No. | 산출물 | 요구사항 지정 파일 |
|--:|---|---|
| 1 | 학습용 Dataset Version | `configs/dataset.yaml` |
| 1 | | `manifests/split_manifest.csv` |
| 1 | | `manifests/train.csv` · `val.csv` · `test.csv` · `bridge_holdout.csv` |
| 1 | | `docs/split_policy.md` |
| 1 | | `reports/dataset_summary.csv` |
| 2 | Baseline Model | `models/baseline/baseline_best.pt` |
| 2 | | `runs/baseline_v1/results.csv` |
| 2 | | `reports/baseline_training_condition.md` |
| 2·5 | | `reports/baseline_metrics.csv` |
| 3 | Failure Analysis | `reports/failure_analysis.csv` |
| 3 | | `demo/failure_analysis/*.jpg` |
| 3 | | `reports/failure_hypothesis.md` |
| 4 | Improved / Final Model | `models/improved/exp001_best.pt` |
| 4 | | `models/final/final_best.pt` |
| 4 | | `reports/improvement_experiment.md` |
| 4 | | `reports/final_model_selection.md` |
| 5 | 성능·실험 기록 | `reports/experiment_log.csv` |
| 5 | | `reports/final_metrics.csv` |
| 5 | | `reports/baseline_vs_improved.md` |
| 5 | | `reports/figures/` — `baseline_results` · `baseline_confusion_matrix` · `exp001_results` · `exp001_confusion_matrix` · `final_test_confusion_matrix` (.png) |
| 6 | Detection · Auto Label | `demo/prediction_images/` |
| 6 | | `demo/auto_label/candidate_labels/` |
| 6 | | `demo/auto_label/reviewed_labels/` |
| 6 | | `reports/auto_label_review.csv` |
| 7 | 문서·후속 프로젝트 연결 | `README.md` |
| 7 | | `reports/acceptance_test.md` |
| 7 | | `docs/handoff_subject14.md` |
| 8 | 최종 발표·시연 | `presentation/final_presentation.pdf` |
| 8 | | `presentation/qna_guide.md` |
| 8 | | `demo/final_detection_demo.mp4` (또는 실시간 시연) |
| 8 | | `demo/auto_label_human_review_demo.mp4` (또는 실시간 시연) |

---

## 2. 우리 산출물 (B) — 왜 만들었나

| 파일 | 만든 코드 | 왜 만들었나 |
|---|---|---|
| `reports/audit_expected.md` | 사람 작성 | Audit **실행 전에** 라벨 검수 단계 문서 기준 기대값을 먼저 고정. 결과를 보고 기준을 바꾸지 않기 위해 (Test Oracle) |
| `reports/audit_check.csv` | `03_audit_subject7_final.py` | 기대값 vs 실제 19항목 비교 → 검수 완료 데이터셋 900장이 맞다는 **PASS 증거** |
| `reports/audit_label_stats.csv` | `03_audit_subject7_final.py` | 이미지별 BBox · Class 수 · 출처 · scene_type 정리 → Split 계산(04 · 05)의 **입력** |
| `reports/class_scene_distribution.csv` | `04_split_analysis.py` | 요구사항 §15.2 "Scene Type과 Class 분포 확인"의 결과를 파일로 남김 |
| `reports/filename_time_check.csv` | `04_split_analysis.py` | 사진에 EXIF 촬영시각이 없어서, **파일명 시각**을 촬영시각으로 써도 되는지 확인 |
| `reports/capture_groups.csv` | `04_split_analysis.py` | 이미지별 촬영시각 + 1 · 5 · 10분 세션 번호 → 연속 촬영 사진이 Train과 Test에 갈라지는 **Leakage 방지**용 묶음. 05의 입력 |
| `reports/capture_group_compare.csv` | `04_split_analysis.py` | 1 · 5 · 10분 기준별 세션 수(106 · 18 · 13) 비교 → **5분 기준을 고른 근거** |
| `reports/capture_group_summary.csv` | `04_split_analysis.py` | 5분 세션 G01~G18 상세 (시각 · 이미지 · Class 수) |
| `splits/kimchi_v1_split.csv` | `05_make_split.py` | Freeze **전** 배정 후보. 바로 `manifests/`에 쓰지 않고 검사 후 확정하려고 한 단계를 나눔 |
| `reports/split_check.csv` | `05_make_split.py` | 배정 합격 기준 8개 PASS / FAIL (같은 세션이 다른 역할에 섞이지 않음 등) |
| `reports/split_summary.csv` | `05_make_split.py` | 역할별 이미지 · BBox · Class · 세션 수 (600 / 74 / 80 / 146) |
| `reports/freeze_check.csv` | `06_freeze_split.py` | Freeze 전 13항목 검사 → 전부 PASS일 때만 `manifests/` 생성 |
| `reports/manifest_schema_check.csv` | `upgrade_manifest_schema_v1_to_v2.py` | `manifests/`를 요구사항 §16.1 최소 컬럼(v2)으로 바꿀 때 **배정이 하나도 안 바뀌었다**는 증명 |
| `reports/yolo_build_summary.csv` | `08_build_yolo_dataset.py` | `data/yolo/`(Git 제외)로 복사한 결과의 역할별 수량 · Test 지문 |
| `reports/yolo_verify_check.csv` | `09_verify_yolo_dataset.py` | 복사한 학습 폴더가 manifest와 **정확히 일치**하는지 19항목 검증 |
| `reports/label_preview.md` | 사람 작성 | 요구사항 §16.4 "라벨 다시 시각화" 활동 결과(20장 · 20/20 일치) 기록. 요구사항 문서는 활동만 지정하고 파일은 지정 안 함 |
| `configs/baseline.yaml` | 사람 작성 (팀 확정) | 학습 조건을 코드 밖 파일로 고정 → 누가 돌려도 같은 조건 |
| `reports/baseline_results.csv` | `10_train_baseline.py` | `runs/`는 Git 제외라서 `results.csv`의 **숫자만 사본**으로 남김 |
| `reports/baseline_val_image_check.csv` | `11_evaluate_baseline.py` | 이미지별 TP · FP · FN · 작은 객체 FN → Failure Analysis의 **입력** |
| `reports/baseline_class_check.csv` | `11_evaluate_baseline.py` | conf 0.25 기준 Class별 Recall · Precision → 개선 실험 단계 개선 비교의 **기준** |
| `reports/figures/baseline_confusion_matrix_normalized.png` | `11_evaluate_baseline.py` | 개수 그림은 background 칸이 수천 개라 읽기 어려워서 **비율** 그림을 추가 |
| `reports/branch_pred_check.csv` | `12_branch_fp_check.py` | 나뭇가지 오검출이 진짜 모델 오류인지, **라벨 누락**인지 사람이 하나씩 확인 → 가설 H3 근거 |
| `reports/failure_image_list.csv` | `13_failure_images.py` | 실패 비교 그림(`demo/`)은 NDA로 Git 제외 → 어떤 사진인지 **숫자 목록**만 남김 |
| `configs/exp001.yaml` | 사람 작성 | `baseline.yaml` 복사 + imgsz 640 → 1280 **한 줄만** 변경 → "변수 하나만 바꿨다"를 파일 비교로 증명 |
| `reports/exp001_training_condition.md` | `14_train_experiment.py` | 요구사항 문서는 Baseline 조건 문서만 지정. 개선 실험도 **같은 형식**으로 남겨 비교 가능하게 함 |
| `reports/exp001_results.csv` | `14_train_experiment.py` | `runs/exp001/results.csv` 숫자 사본 (Git 제외 대응) |
| `reports/exp001_metrics.csv` | `15_evaluate_experiment.py` | `baseline_metrics.csv`와 **같은 형식** → 나란히 비교 |
| `reports/exp001_class_check.csv` | `15_evaluate_experiment.py` | `baseline_class_check.csv`와 같은 기준으로 Class별 비교 |
| `reports/exp001_val_image_check.csv` | `15_evaluate_experiment.py` | `baseline_val_image_check.csv`와 같은 기준으로 이미지별 비교 |
| `reports/figures/exp001_confusion_matrix_normalized.png` | `15_evaluate_experiment.py` | Baseline과 같은 이유 (비율 그림) |
| `reports/final_test_runs.csv` | `16_evaluate_final_test.py` | Frozen Test를 **딱 1번만** 열었다는 실행 기록 |
| `reports/final_class_check.csv` | `16_evaluate_final_test.py` | Test Class별 GT · TP · FN · FP |
| `reports/final_test_image_check.csv` | `16_evaluate_final_test.py` | Test 이미지별 결과 → 후속 프로젝트에 넘길 **대표 FP / FN 근거** |
| `reports/figures/final_test_confusion_matrix_normalized.png` | `16_evaluate_final_test.py` | 비율 그림 |
| `reports/figures/final_test_pr_curve.png` | `16_evaluate_final_test.py` | Class별 Precision–Recall 곡선 (발표 · 후속 프로젝트 설명용) |
| `reports/auto_label_candidates.csv` | `17_auto_label.py` | 후보 라벨 TXT(`demo/`)는 Git 제외 → 사진별 후보 BBox 수 · Class **숫자만** 남김 |
| `daily_csv/10_12.csv` ~ `10_15.csv` | 사람 작성 · 팀 기록 | 단계별 작업 · **작성자** 기록 → 팀원별 역할과 작업 내역 확인 (기준선 8번) |
| `docs/code_review/` (26개) | 사람 작성 · 팀 기록 | 주요 코드 리뷰 기록 (기준선 3번) |
| `docs/code_flow.md` · `docs/figures/*.svg` (7장) | 사람 작성 · 팀 기록 | 스크립트 실행 순서 · import 관계 그림 → 처음 보는 사람이 코드 흐름을 파악하도록 |

---

