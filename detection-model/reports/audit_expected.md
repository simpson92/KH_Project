# Audit 기대값 메모 (라벨 검수 → 검출 모델)

> **용도**: `src/dataset_audit.py` 실행 결과를 대조할 **기대값(Test Oracle)**
> **구분**: 진행용 보조기록 · 최종 산출물 아님
> **문서 버전**: **v2** (2026-10-13) · 기준 데이터 **`kimchi_v1`** (라벨 지문 `5c2b4fc2c3e6`) · 개정 이력은 [9장](#9-개정-이력)
> **작성**: v1 2026-10-12 · 최용훈 (라벨 검수 단계 문서 정리) / v2 2026-10-13 · 최용훈 (kimchi_v1 확정 반영)
> **원칙**: Audit 결과를 보고 이 파일의 숫자를 바꾸지 않는다. 결과가 다르면 먼저 `reports/audit_issue.csv` · `reports/issue_log.md`에 기록하고 원인을 찾는다. 기대값은 **근거 문서 + 팀 합의 + 개정 이력**이 모두 있을 때만 개정한다 (8장 규칙 4).

## 0. 출처 문서

| 약어 | 문서 | 내용 |
|---|---|---|
| H | `labeling-qa-tool/docs/subject08_handoff.md` | 검출 모델 단계 인계 · 주의사항 |
| Q | `labeling-qa-tool/reports/qa_summary.md` | QA · Validation · Class별 BBox (10/07 기준) |
| M | `labeling-qa-tool/manifests/dataset_manifest.csv` | 900장 출처 · split · scene_type · 검수 상태 |
| D1 | 2026-10-12 환경 구성 단계 직접 확인 | `data/subject7_final` 기준 |
| **V1** | `docs/split_policy.md` 결정 기록 · `README.md` Dataset Version | **kimchi_v1 = 10/08 수정본 (4,601)** 팀 확정 · 5명 라벨 지문 일치 (2026-10-12) |

> ⚠️ H · Q는 10/07 QA 기준이라 10/08 라벨 추가 수정이 빠져 있다. **Class별 BBox(2장)는 V1을 기준**으로 한다. 나머지 장은 10/08 수정의 영향을 받지 않는다 (9장 참고).

---

## 1. 파일 · 형식 검사 기대값

| 검사 항목 | 기대값 | 출처 | 환경 구성 단계 확인 | 데이터 감사 단계 Audit (v1) |
|---|---:|---|---|---|
| JPG 수 | 900 | H, Q | ✅ 900 | ✅ 900 |
| TXT 수 | 900 | H, Q | ✅ 900 | ✅ 900 |
| JPG ↔ TXT Pair 일치 | 900 | H, Q | | ✅ 900 |
| Pair 누락 (TXT 없음 / JPG 없음) | 0 / 0 | Q 5.4 | | ✅ 0 / 0 |
| Empty TXT | 0 | H 8.1, Q 5.2 | ✅ 0 | ✅ 0 |
| Class 4 포함 TXT | 0 | H 8.2, Q 5.4 | ✅ 0 | ✅ 0 |
| Class ID 범위 오류 (0~6 밖) | 0 | Q 2 | | ✅ 0 (`format_errors`에 포함) |
| 좌표 형식 오류 (칸 수 · 숫자 변환) | 0 | Q 2 | | ✅ 0 (`format_errors`에 포함) |
| 좌표 범위 오류 (0~1 밖) | 0 | Q 2 | | ✅ 0 (`format_errors`에 포함) |
| Manifest 행 수 | 900 | M | ✅ 900 | ✅ 900 |
| QA 상태 | 900장 전체 PASS | M, Q | ✅ PASS 900 | (Audit 대상 아님) |

## 2. Class별 BBox 기대값 (kimchi_v1, 총 4,601개)

| Class | 이름 | v2 기대값 (kimchi_v1) | 비율 | v1 기대값 (라벨 검수 단계 문서) | 변화 |
|:-:|---|---:|---:|---:|---:|
| 0 | 나뭇잎·종이류 | **924** | 20.1% | 868 | +56 |
| 1 | 플라스틱류·돌·금속류 | 1,897 | 41.2% | 1,897 | 0 |
| 2 | 나뭇가지류 | **711** | 15.5% | 767 | −56 |
| 3 | 벌레류 | 378 | 8.2% | 378 | 0 |
| 4 | 고무장갑 (미사용) | 0 | 0.0% | 0 | 0 |
| 5 | 병해·갈변 | **439** | 9.5% | 441 | −2 |
| 6 | 파·고추 | **252** | 5.5% | 251 | +1 |
| | **합계** | **4,601** | 100% | 4,602 | **−1** |

- 출처: **V1** (kimchi_v1 확정 · `docs/split_policy.md` 1장 · `README.md` Class 표)
- 변화 원인: 10/07 QA 이후 이승훈 10/08 라벨 추가 수정 (Class 2→0 56개 등) · 근거 `reports/issue_log.md` 10/12
- 이미지당 평균 BBox: 4,601 / 900 = **약 5.1개**
- Class 불균형: Class 1 ÷ Class 6 = 1,897 ÷ 252 = **약 7.5배** (v1: 1,897 ÷ 251 ≈ 7.6배)
- ⚠️ 이 숫자는 **라벨 지문이 `5c2b4fc2c3e6`일 때만** 유효하다. 지문이 다르면 Audit 결과를 비교하기 전에 데이터 버전부터 확인한다 (8장 규칙 0).

## 3. 출처 · scene_type 기대값

| source_dataset / original_split | kimchi_with_target | object_only | normal_kimchi | 합계 |
|---|---:|---:|---:|---:|
| dataset1 / train | 500 | 0 | 0 | 500 |
| dataset2 / train | 100 | 120 | 0 | 220 |
| dataset2 / validation | 150 | 30 | 0 | 180 |
| **합계** | **750** | **150** | **0** | **900** |

- 출처: H 8.1, M (Manifest 재집계로 일치 확인 · 2026-10-12)
- other_review: 0장

## 4. 촬영 날짜 분포 (Manifest 파일명 앞 6자리 기준)

| 날짜 (YYMMDD) | dataset1 train | dataset2 train | dataset2 validation | scene_type |
|---|---:|---:|---:|---|
| 250410 | 115 | 0 | 35 | 전부 kimchi_with_target |
| 250411 | 203 | 0 | 47 | 전부 kimchi_with_target |
| 250424 | 182 | 100 | 68 | 전부 kimchi_with_target |
| 250513 | 0 | 120 | 30 | 전부 object_only |

- 출처: M 재집계 (2026-10-12)
- ✅ 파일명 = 촬영 순서 확인 (2026-10-12 · EXIF 없음 · 250410 연속 3장 육안 확인, `docs/split_policy.md`)

## 5. Data Leakage 사전 확인 (Manifest 파일명 시간 기준)

| 확인 항목 | 값 | 출처 |
|---|---|---|
| 기존 validation 중 60초 이내에 촬영된 train 이미지가 있는 장 수 | **136 / 180 (75.6%)** | H 8.2-3, M 재계산 일치 |
| validation ↔ 가장 가까운 train 최소 시간차 | **8초** | H 8.2-3, M 재계산 일치 |
| 촬영 간격 5분 이상을 세션 경계로 볼 때 세션 수 | 18개 (참고) | M 재계산 |
| 그중 train과 validation이 섞인 세션 | 17개 (참고) | M 재계산 |

- 해석: 기존 train / validation은 **촬영 세션 단위로 나뉘지 않았다.** 기존 validation을 그대로 Validation으로 쓰면 점수가 부풀 가능성이 높다.
- 세션 경계 기준은 데이터 감사 단계 회의에서 **5분**으로 확정 (`docs/split_policy.md`).
- ℹ️ 검출 모델 단계 코드(`04_split_analysis.py`)는 **135**로 계산한다. 1장이 60.28초 차이라 초 단위 절사(라벨 검수 단계) / 마이크로초 계산(검출 모델 단계)에 따라 갈린다. 결론에 영향이 없어 **기대값 136 유지**로 팀 결정 (`reports/issue_log.md` 10/12). 이 항목은 v2에서도 바꾸지 않는다.

## 6. 이미 알려진 주의사항 → Split 정책 안건

| # | 주의사항 | 근거 | Split 정책에서 정할 것 |
|---|---|---|---|
| 1 | 정상 김치(Negative) **0장** | H 8.2-1, Q 5.2 | 정상 김치 FP 평가 방법 · 알려진 한계로 기록 |
| 2 | object_only 150장이 **전부 dataset2 · 250513** | 3장, 4장 | 날짜 단위로 나누면 한 역할에 몰림 → 어떻게 배분할지 |
| 3 | 기존 train ↔ validation **유사 장면 75.6%** | 5장 | 기존 validation을 그대로 쓸지, 세션 단위로 다시 나눌지 |
| 4 | Class 4 **0건** | H 8.2-4 | 보고서에 "미사용 Class / Instance 0건" 기록 |
| 5 | Class 불균형 **7.5배** (v1 문서 7.6배) | 2장 | 각 역할에 모든 Class가 충분히 들어가는지 확인 |
| 6 | `too_small_to_identify` REVIEW **19장** | Q 5.3 | 작은 객체 FN 후보 → Failure Analysis 참고 |

## 7. 문서 간 차이 메모 (QA 관점)

| 항목 | 차이 | 이 메모의 기준 |
|---|---|---|
| REVIEW 사유 수 | Q 3장 표 10 / 1 / 29 ↔ Q 5.3 · H 7 / 1 / 19 | 실제 이미지 수 **7 / 1 / 19 (27장)** (Q 3장은 이력 줄 수 기준, Q에 주석 있음) |
| Class 1 이름 | 요구사항 문서 "금속 등" ↔ 라벨 검수 단계 "금속류" | 라벨 검수 단계 `classes.yaml` 표기 **"금속류"** |
| FINAL 위치 | H 2장 `data/final/` ↔ 실제 `~/exe_01/master_data/final/` | 검출 모델 단계은 복사본 **`detection-model/data/subject7_final/`** 사용 |
| **Class별 BBox** | H 8.1 · Q 5.5 **4,602** (10/07 QA) ↔ FINAL 라벨 **4,601** (10/08 수정) | **kimchi_v1 (4,601)** · v2에서 2장 개정 |

## 8. Audit 판정 규칙

0. **Audit 전에 라벨 지문부터 확인한다.** `LC_ALL=C cat data/subject7_final/labels/*.txt | sha256sum | cut -c1-12` → `5c2b4fc2c3e6`가 아니면 Audit을 돌리지 말고 데이터 버전을 맞춘다 (10/12 팀원 2명 옛 버전 사용 사례).
1. Audit 결과가 이 메모와 **같으면** → PASS, 기록에 "기대값 일치 (v2)"로 남긴다.
2. **다르면** → 데이터도, 이 메모도 바로 고치지 않는다. `reports/audit_issue.csv`에 `항목 · 기대값 · 실제값 · 파일명 · 추정 원인`을 기록하고 팀이 원인을 확인한다.
3. 라벨 수정이 꼭 필요하면 수정 근거를 기록하고 **Dataset Version을 올린다** (예: `kimchi_v1 → kimchi_v2`, 요구사항 §11.5).
4. **기대값 개정 조건**: 원인이 "데이터 결함"이 아니라 "기준 문서가 낡음"으로 확인되고, 새 기준이 팀 합의로 고정(Dataset Version · 지문)된 경우에만 개정한다. 개정 시 9장에 이유 · 근거 · 바뀐 항목을 남기고, 이전 실행 결과는 지우지 않는다.
5. 라벨 검수 단계 라벨 QA를 처음부터 다시 하지 않는다.

## 9. 개정 이력

| 버전 | 날짜 | 작성 | 내용 | 기준 데이터 | Audit 결과 |
|---|---|---|---|---|---|
| v1 | 2026-10-12 | 최용훈 | 라벨 검수 단계 문서(H · Q · M) 기준 최초 작성 | 라벨 검수 단계 문서 (10/07 QA · 4,602) | PASS 14 / FAIL 5 (bbox_total · class_0 · class_2 · class_5 · class_6) |
| v2 | 2026-10-13 | 최용훈 | 2장 Class별 BBox를 kimchi_v1으로 개정 · 6장 #5 불균형 7.5배 · 7장 차이 메모 추가 · 8장 규칙 0 · 4 추가 | **kimchi_v1** (10/08 수정본 · 4,601 · 지문 `5c2b4fc2c3e6`) | **PASS 19 / FAIL 0** (2026-10-13 재실행 · 지문 `5c2b4fc2c3e6` 확인) |

**v2 개정 근거**

- v1 FAIL 5건의 원인은 **데이터 결함이 아니라 기준 문서 미반영**으로 확인됨: 10/07 QA 이후 10/08 라벨 추가 수정이 H · Q에 반영되지 않음. 이승훈 10/08 zip = master = subject7_final (diff 0) (`reports/issue_log.md` 10/12)
- 팀 전원이 **kimchi_v1 = 10/08 수정본 (4,601)** 으로 확정하고 5명 라벨 지문 `5c2b4fc2c3e6` 일치 확인 (`docs/split_policy.md` 결정 기록, `README.md`)
- 바뀐 항목은 2장 Class별 BBox 5개 (bbox_total · class_0 · class_2 · class_5 · class_6)뿐이다. 1 · 3 · 4 · 5장은 라벨 수정과 무관하므로 v1 그대로다.
- v1 실행 결과(PASS 14 / FAIL 5)는 `reports/issue_log.md`, `daily_csv/10_12.csv`, Git 이력(`reports/audit_check.csv`, 커밋 `70f32e1`)에 보존한다.
