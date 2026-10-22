# 코드 리뷰 (파일별)

> **기준**: `main` · PR #73 (2026-10-12) · `detection-model/`
> **구성**: 실제 코드와 **같은 폴더 구조**로 파일마다 리뷰 문서 1개
> **용도**: 10/13 리뷰 데이 · 코드 리뷰 / 프로젝트 리뷰

## 리뷰 문서 구조

```
docs/code_review/
├── README.md                          # 이 문서 · 목차 · 읽는 순서 · 표기법
├── configs/
│   └── dataset_yaml.md                # configs/dataset.yaml
├── src/
│   ├── dataset_audit.md               # src/dataset_audit.py
│   ├── capture_group.md               # src/capture_group.py
│   ├── manifest.md                    # src/manifest.py
│   ├── train_detector.md              # src/train_detector.py
│   └── evaluate_detector.md           # src/evaluate_detector.py
└── scripts/
    ├── 01_check_environment.md        # scripts/01_check_environment.py
    ├── 02_make_audit_fixture.md      # scripts/02_make_audit_fixture.py
    ├── 03_audit_subject7_final.md     # scripts/03_audit_subject7_final.py
    ├── 04_split_analysis.md           # scripts/04_split_analysis.py
    ├── 05_make_split.md               # scripts/05_make_split.py
    ├── 06_freeze_split.md             # scripts/06_freeze_split.py
    ├── 07_dataset_summary.md         # scripts/07_dataset_summary.py
    ├── upgrade_manifest_schema_v1_to_v2.md # scripts/archive/upgrade_manifest_schema_v1_to_v2.py
    ├── 08_build_yolo_dataset.md       # scripts/08_build_yolo_dataset.py
    ├── 09_verify_yolo_dataset.md      # scripts/09_verify_yolo_dataset.py
    ├── 10_train_baseline.md           # scripts/10_train_baseline.py
    ├── 11_evaluate_baseline.md        # scripts/11_evaluate_baseline.py
    ├── 12_branch_fp_check.md         # scripts/12_branch_fp_check.py
    ├── 13_failure_images.md          # scripts/13_failure_images.py
    ├── 14_train_experiment.md         # scripts/14_train_experiment.py
    ├── 15_evaluate_experiment.md      # scripts/15_evaluate_experiment.py
    ├── 16_evaluate_final_test.md      # scripts/16_evaluate_final_test.py
    ├── 17_auto_label.md               # scripts/17_auto_label.py
    └── 18_auto_label_review.md        # scripts/18_auto_label_review.py
```

`src/__init__.py`는 내용이 없는 파일(“src를 패키지로 인식시키는 표시”)이라 별도 문서를 만들지 않았습니다.

## 실제 코드 ↔ 리뷰 문서

| 코드 | 단계 | 줄 수 | 한 줄 역할 | 리뷰 문서 |
|---|:-:|--:|---|---|
| `configs/dataset.yaml` | 1 | 14 | YOLO가 읽는 데이터 경로 · Class 이름 | [dataset_yaml.md](configs/dataset_yaml.md) |
| `src/dataset_audit.py` | 2 | 216 | 데이터 "건강검진" 함수 모음 | [dataset_audit.md](src/dataset_audit.md) |
| `src/capture_group.py` | 2 | 54 | 파일명 → 촬영 시각 · 촬영 세션 묶기 | [capture_group.md](src/capture_group.md) |
| `src/manifest.py` | 3 | 103 | manifest v1 · v2 · split CSV를 같은 모양(`split` 키)으로 읽고 · 비교하고 · 쓰기 | [manifest.md](src/manifest.md) |
| `src/train_detector.py` | 4 | 43 | YOLO 학습 공통 함수 (`TRAIN_KEYS` 12개만 전달) | [train_detector.md](src/train_detector.md) |
| `src/evaluate_detector.py` | 5 | 94 | Val 평가 · 이미지 예측 · TP/FP/FN 짝짓기 (Frozen Test 보호) | [evaluate_detector.md](src/evaluate_detector.md) |
| `scripts/01_check_environment.py` | 1 | 36 | 환경 · GPU · YOLO Load 확인 | [01_check_environment.md](scripts/01_check_environment.md) |
| `scripts/02_make_audit_fixture.py` | 2 | 76 | 버그 9종을 심은 테스트 데이터 | [02_make_audit_fixture.md](scripts/02_make_audit_fixture.md) |
| `scripts/03_audit_subject7_final.py` | 2 | 118 | 900장 Audit + 기대값 대조 | [03_audit_subject7_final.md](scripts/03_audit_subject7_final.md) |
| `scripts/04_split_analysis.py` | 2 | 202 | 분포 · EXIF · 세션 비교 · Leakage | [04_split_analysis.md](scripts/04_split_analysis.md) |
| `scripts/05_make_split.py` | 3 선행 | 266 | 전수 탐색 배정 + 합격 기준 검증 | [05_make_split.md](scripts/05_make_split.md) |
| `scripts/06_freeze_split.py` | 3 | 149 | 13항목 검사 후 `manifests/`(스키마 v2)로 Split Freeze | [06_freeze_split.md](scripts/06_freeze_split.md) |
| `scripts/07_dataset_summary.py` | 3 | 128 | 8항목 검사 후 Dataset Version 요약표(`dataset_summary.csv`) 작성 | [07_dataset_summary.md](scripts/07_dataset_summary.md) |
| `scripts/archive/upgrade_manifest_schema_v1_to_v2.py` | 3 보완 | 117 | `manifests/` v1(3칸) → v2(9칸) 업그레이드 · 배정 변경 0 | [upgrade_manifest_schema_v1_to_v2.md](scripts/archive/upgrade_manifest_schema_v1_to_v2.md) |
| `scripts/08_build_yolo_dataset.py` | 3 | 182 | Split 목록으로 `data/yolo` 학습 폴더 구성 (Bridge 제외) | [08_build_yolo_dataset.md](scripts/08_build_yolo_dataset.md) |
| `scripts/09_verify_yolo_dataset.py` | 3 | 134 | `data/yolo`가 Freeze 본과 같은지 19항목 검증 | [09_verify_yolo_dataset.md](scripts/09_verify_yolo_dataset.md) |
| `scripts/10_train_baseline.py` | 4 | 300 | 학습 전 12항목 검사 → Baseline 학습 → 조건 문서 자동 기록 | [10_train_baseline.md](scripts/10_train_baseline.md) |
| `scripts/11_evaluate_baseline.py` | 5 | 323 | Val 평가 · Class별 지표 · 이미지별 FP/FN · Class별 TP/FN/FP (Test · Bridge 미사용) | [11_evaluate_baseline.md](scripts/11_evaluate_baseline.md) |
| `scripts/12_branch_fp_check.py` | 6 준비 | 275 | Val branch 예측을 5종으로 분류 · 사람 확인 칸 (가설 H3 · 오검출 확인) | [12_branch_fp_check.md](scripts/12_branch_fp_check.md) |
| `scripts/13_failure_images.py` | 6 | 184 | 대표 실패 사례 Val 사진에 정답(초록 · 노랑) + 예측(빨강)을 겹친 비교 그림 (`demo/` · Git 제외) | [13_failure_images.md](scripts/13_failure_images.md) |
| `scripts/14_train_experiment.py` | 7 | 245 | 한 변수 원칙 검사 → Smoke · Dry-run · 개선 실험 학습 → Improved Weight 보관 · 조건 문서 | [14_train_experiment.md](scripts/14_train_experiment.md) |
| `scripts/15_evaluate_experiment.py` | 7 | 252 | 11 채점 함수 그대로 개선 모델 Val 평가 → Baseline 비교 · `experiment_log.csv` · 비교 md 초안 (Test 미사용) | [15_evaluate_experiment.md](scripts/15_evaluate_experiment.md) |
| `scripts/16_evaluate_final_test.py` | 8 | 285 | 선택 문서 커밋 · Final sha · Test 지문 등 15항목 검사 → Frozen Test **1회** 평가 (11 채점 함수 그대로 · 1회 잠금) | [16_evaluate_final_test.md](scripts/16_evaluate_final_test.md) |
| `scripts/17_auto_label.py` | 8 | 215 | Frozen Test 평가 뒤 Test 사진 8장으로 Detection 이미지 · Auto Label 후보 TXT · 라벨 검수 단계 검수 폴더 준비 (정답은 숨김) | [17_auto_label.md](scripts/17_auto_label.md) |
| `scripts/18_auto_label_review.py` | 8 | 172 | AI 후보 vs 사람 검수 1:1 비교 → 승인 · Class 수정 · BBox 수정 · 삭제 · 누락 추가 집계 | [18_auto_label_review.md](scripts/18_auto_label_review.md) |

## 그림은 어디에?

| 보고 싶은 것 | 위치 |
|---|---|
| 파일 **하나 안**의 흐름 (함수 순서 · 분기) | 각 리뷰 문서 3장 **흐름 그림** |
| 파일 **사이**의 흐름 (무엇을 읽고 무엇을 넘기나) · import 관계 | [`../code_flow.md`](../code_flow.md) |

같은 그림을 두 곳에 두지 않습니다. 코드를 고치면 **그 파일의 리뷰 문서 그림 하나만** 고치면 됩니다.

## 읽는 순서 (추천)

데이터가 흐르는 순서대로 읽으면 이해가 쉽습니다.

```
01_check_environment → dataset_yaml
      ↓
dataset_audit (기능) → 02_make_audit_fixture → 03_audit_subject7_final
      ↓  audit_label_stats.csv
capture_group (기능) → 04_split_analysis
      ↓  capture_groups.csv  +  docs/split_policy.md (사람의 결정)
05_make_split
      ↓  splits/kimchi_v1_split.csv
06_freeze_split  ←→  manifest (기능: read_manifest · build_v2_rows · write_manifest_set)
      ↓  manifests/split_manifest.csv
upgrade_manifest_schema_v1_to_v2 (v1 → v2) → 07_dataset_summary
      ↓  manifests/ (v2) · reports/dataset_summary.csv
08_build_yolo_dataset
      ↓  data/yolo
09_verify_yolo_dataset
      ↓
train_detector (기능) → 10_train_baseline
      ↓  models/baseline/baseline_best.pt · reports/baseline_training_condition.md
evaluate_detector (기능) → 11_evaluate_baseline
      ↓  reports/baseline_val_image_check.csv · baseline_class_check.csv
12_branch_fp_check  (실패 분석 단계 · branch 오검출 확인 · reports/branch_pred_check.csv)
      ↓  reports/failure_analysis.csv (사람이 대표 실패 사례 정리)
13_failure_images  (실패 분석 단계 · GT vs 예측 비교 그림 · demo/failure_analysis/)
      ↓  reports/improvement_experiment.md (사람의 결정 · 바꿀 변수 하나 · 상태: 확정)
14_train_experiment  (개선 실험 단계 · --smoke → --dry-run → 본 학습 · 10 도우미 재사용)
      ↓  models/improved/exp001_best.pt · reports/exp001_training_condition.md
15_evaluate_experiment  (개선 실험 단계 · 11 채점 함수 그대로 · Baseline 비교)
      ↓  reports/experiment_log.csv · reports/baseline_vs_improved.md (해석 · 결정은 팀)
      ↓  reports/final_model_selection.md (사람의 결정 · Final = exp001 · Test 전에 커밋)
16_evaluate_final_test  (Final 선정 단계 · Frozen Test 1회 · 11 채점 함수 그대로 · 1회 잠금)
      ↓  reports/final_metrics.csv (= Test 사진을 써도 된다는 신호)
17_auto_label  (Final 선정 단계 · Test 8장 · Detection · 후보 TXT · 검수 폴더 · 정답 숨김)
      ↓  라벨 검수 도구 (사람 검수 → review_workspace/work · final)
18_auto_label_review  (Final 선정 단계 · 후보 vs 검수 집계 · reports/auto_label_review.csv)
```

## 표기법

모든 리뷰 문서는 같은 순서로 씁니다.

1. **한 줄 요약** — 이 파일이 왜 필요한가
2. **입력 · 출력 · 실행** — 무엇을 받아서 무엇을 만드나
3. **구조** — 함수 · 구간별 위치(줄 번호) + **흐름 그림**(Mermaid · 이 파일 **안에서만** 어떤 순서로 도나 · 다른 파일 이야기는 넣지 않음)
4. **핵심 코드 읽기** — 중요한 코드 발췌와 짧은 설명

가져다 쓰는 코드 · 기준값 출처처럼 파일 **사이** 관계는 2장 표에 한 줄로 적고, 전체 그림은 [`../code_flow.md`](../code_flow.md)에서 봅니다.
