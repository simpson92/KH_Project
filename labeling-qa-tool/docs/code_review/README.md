# 코드 리뷰 (파일별)

> **기준**: `main` · `cbf3d10` (2026-10-20) · `labeling-qa-tool/` · 라벨링 프로그램 v4.1
> **구성**: 실제 코드와 **같은 폴더 구조**로 파일마다 리뷰 문서 1개 · 코드 17개 = 리뷰 17개 ([검출 모델 코드 리뷰](../../../detection-model/docs/code_review/README.md)와 같은 방식)

## 리뷰 문서 구조

```
docs/code_review/
├── README.md                     # 이 문서 · 목차 · 읽는 순서 · 리뷰에서 찾은 점 · 표기법
├── main.md                       # main.py
├── configs/
│   └── classes_yaml.md           # configs/classes.yaml
├── src/
│   ├── yolo/
│   │   ├── yolo_loader.md        # src/yolo/yolo_loader.py
│   │   └── yolo_writer.md        # src/yolo/yolo_writer.py
│   ├── bbox/
│   │   ├── bbox_manager.md       # src/bbox/bbox_manager.py
│   │   └── bbox_editor.md        # src/bbox/bbox_editor.py
│   ├── ui/
│   │   ├── main_window.md        # src/ui/main_window.py
│   │   ├── canvas.md             # src/ui/canvas.py
│   │   └── validation_window.md  # src/ui/validation_window.py
│   ├── records/
│   │   ├── manifest.md           # src/records/manifest.py
│   │   └── history.md            # src/records/history.py
│   ├── validation/
│   │   └── validator.md          # src/validation/validator.py
│   └── qa/
│       ├── self_test.md          # src/qa/self_test.py
│       └── reports.md            # src/qa/reports.py
└── tools/
    ├── label_stats.md            # tools/label_stats.py
    ├── make_reports.md           # tools/make_reports.py
    └── merge_results.md          # tools/merge_results.py
```

`__init__.py` 파일들은 내용이 없는 파일("이 폴더를 패키지로 인식시키는 표시")이라 별도 문서를 만들지 않았습니다.

## 실제 코드 ↔ 리뷰 문서

| 코드 | 줄 수 | 한 줄 역할 | 리뷰 문서 |
|---|--:|---|---|
| `main.py` | 94 | 프로그램 시작 · `classes.yaml` 읽고 검사 → 화면 띄우기 | [main.md](main.md) |
| `configs/classes.yaml` | 75 | Class · 팀원 · scene_type · review_reason · 팀 규칙(`allow_self_review` 등) | [classes_yaml.md](configs/classes_yaml.md) |
| `src/yolo/yolo_loader.py` | 279 | data 폴더 → 900장 작업 목록 · 단계별 라벨 경로 · TXT 읽기 · 원본 지문 | [yolo_loader.md](src/yolo/yolo_loader.md) |
| `src/yolo/yolo_writer.py` | 129 | TXT 저장 · work / final 이동 · raw 쓰기 금지 · raw → final 직행 금지 | [yolo_writer.md](src/yolo/yolo_writer.md) |
| `src/bbox/bbox_manager.py` | 110 | BBox 데이터 (생성 · 수정 · 삭제 · 되돌리기) · 화면 없이 테스트 가능 | [bbox_manager.md](src/bbox/bbox_manager.md) |
| `src/bbox/bbox_editor.py` | 163 | 마우스로 BBox 그리기 · 이동 · 크기 조절 | [bbox_editor.md](src/bbox/bbox_editor.md) |
| `src/ui/main_window.py` | 1,310 | 화면 · 메뉴 · 단축키 · **저장 버튼 하나로 작업자 저장 / 반려 / QA PASS** | [main_window.md](src/ui/main_window.md) |
| `src/ui/canvas.py` | 402 | 이미지 그리기 · Zoom · Pan · 화면 좌표 ↔ 원본 좌표 | [canvas.md](src/ui/canvas.md) |
| `src/ui/validation_window.py` | 96 | 전체 Validation 결과 창 · 더블클릭으로 이동 | [validation_window.md](src/ui/validation_window.md) |
| `src/records/manifest.py` | 109 | 작업대장 `dataset_manifest.csv` (이미지 1장 = 1줄) | [manifest.md](src/records/manifest.md) |
| `src/records/history.py` | 49 | 작업 이력 `label_history.csv` (누가 · 언제 · 무엇을, 지우지 않음) | [history.md](src/records/history.md) |
| `src/validation/validator.py` | 330 | 설정 검사 · QA PASS 직전 검사 · 900장 Validation (오류 8종) | [validator.md](src/validation/validator.md) |
| `src/qa/self_test.py` | 190 | Golden 20 · Pilot 50 자동 테스트 (임시 폴더 · 원본 그대로) | [self_test.md](src/qa/self_test.md) |
| `src/qa/reports.py` | 501 | 산출물 자동 생성 (7 · 8 · 9 · 11번) · Handoff 패키지 | [reports.md](src/qa/reports.md) |
| `tools/label_stats.py` | 112 | RAW vs FINAL 라벨 통계 (읽기만) | [label_stats.md](tools/label_stats.md) |
| `tools/make_reports.py` | 71 | 화면 없이 산출물 다시 만들기 | [make_reports.md](tools/make_reports.md) |
| `tools/merge_results.py` | 257 | 팀원 결과 묶기(pack) · 합치기(merge) · 충돌 표시 | [merge_results.md](tools/merge_results.md) |

## 그림은 어디에?

| 보고 싶은 것 | 위치 |
|---|---|
| 파일 **하나 안**의 흐름 (함수 순서 · 분기) | 각 리뷰 문서 3장 **흐름 그림** |
| 데이터가 **폴더 사이**로 흐르는 모습 (raw → work → final) | [`../../README.md`](../../README.md) 11장 데이터 위치와 흐름 |

같은 그림을 두 곳에 두지 않습니다. 코드를 고치면 **그 파일의 리뷰 문서 그림 하나만** 고치면 됩니다.

## 읽는 순서 (추천)

데이터가 흐르는 순서대로 읽으면 이해가 쉽습니다.

```
main → classes_yaml                          (시작: 설정 읽기 · 검사)
      ↓
yolo_loader                                  (data 폴더 → 900장 목록 · 라벨 읽기 · 원본 지문)
      ↓
canvas → bbox_editor → bbox_manager          (화면에서 박스 보기 · 고치기)
      ↓
main_window                                  (저장 버튼: 작업자 / 반려 / QA PASS)
      ↓  ↘
yolo_writer          manifest → history      (TXT 를 work · final 로 / 작업대장 · 이력 기록)
      ↓
validator → validation_window                (F7 · 900장 검사 · 결과 창)
      ↓
self_test → reports                          (Golden · Pilot → 산출물 · Handoff)
      ↓
merge_results → make_reports → label_stats   (5명 결과 합치기 → 최종 숫자 · 통계)
```

시간이 없다면 **main_window의 흐름 그림**부터 보세요. 저장 버튼 하나에서 yolo_writer · validator · manifest · history로 이어집니다.

## 리뷰에서 찾은 점

리뷰하면서 확인한 **한계와 개선할 점**입니다. 제출한 v4.1 결과(900장 QA PASS)를 바꾸는 문제는 아니지만, 다음에 같은 도구를 쓸 때 알아 둘 내용입니다. 자세한 설명은 각 문서 4장에 있습니다.

| 문서 | 내용 | 이번 결과에 영향 |
|---|---|---|
| [validator.md](src/validation/validator.md) 4.2 | scene_type 규칙이 `check_scene()`과 `validate_dataset()` 두 곳에 있음 → 한쪽만 고치면 결과가 어긋남 | 없음 (두 곳 내용 같음) |
| [validator.md](src/validation/validator.md) 4.2 · [self_test.md](src/qa/self_test.md) 4.4 | normal_kimchi 0장 + 자동 테스트도 scene_type 규칙을 부르지 않음 → **검증되지 않은 규칙** | 없음 (해당 사진 0장) |
| [reports.md](src/qa/reports.md) 4.3 | REVIEW 사유 "제기된 이미지" 칸이 이미지가 아니라 이력 **줄 수**로 셈 (10/1/29 vs 실제 7/1/19) | 팀이 `qa_summary.md` 5.3에 직접 바로잡음 |
| [reports.md](src/qa/reports.md) 4.4 | Handoff 폴더를 다시 만들 때 같은 이름 라벨은 덮어쓰지 않음 → 고치기 전 TXT가 남을 수 있음 | 받는 쪽(검출 모델 03 Audit)에서 다시 대조 |
| [self_test.md](src/qa/self_test.md) 4.4 | Pilot 50장 중 10장이 Golden 20장과 같은 사진 → 서로 다른 사진은 60장 | 숫자 표현만 주의 |
| [yolo_loader.md](src/yolo/yolo_loader.md) 4.4 | 원본의 형식 오류 줄 · 이미지 밖 박스는 읽을 때 빠지거나 잘려서, 그대로 저장해도 DONE으로 판정 | 최초 Validation(작업 초반)에서 `format` · `bbox_bounds` 0건 (QA Summary 2장) |
| [label_stats.md](tools/label_stats.md) 4.2 | Class 이름 · 인코딩 · 확장자 · 파일 이름 규칙을 본체와 따로 가짐 | 확인한 범위에서는 없음 |
| [history.md](src/records/history.md) 4.1 | 이어 쓰기 인코딩 주석의 이유 설명이 실제 파이썬 동작과 조금 다름 (코드 동작은 올바름) | 없음 |

## 표기법

모든 리뷰 문서는 검출 모델 쪽과 같은 순서로 씁니다.

1. **한 줄 요약**: 이 파일이 왜 필요한가
2. **입력 · 출력 · 실행**: 무엇을 받아서 무엇을 만드나 · 누가 가져다 쓰나
3. **구조**: 함수 · 구간별 위치(줄 번호) + **흐름 그림**(Mermaid · 이 파일 **안에서만** 어떤 순서로 도나)
4. **핵심 코드 읽기**: 중요한 코드 발췌와 짧은 설명 · 알아둘 한계

줄 번호와 코드 발췌는 위 **기준** 커밋의 코드와 같습니다. 코드를 고치면 리뷰 문서의 줄 번호도 함께 고쳐 주세요.
