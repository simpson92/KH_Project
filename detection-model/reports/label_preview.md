# 라벨 Preview 기록

> **구분**: 진행용 보조기록 · 최종 산출물 아님
> **목적**: Split 복사(08) 후 `data/yolo`의 이미지 ↔ TXT 대응과 BBox 위치 · Class가 맞는지 눈으로 확인한다.
> **방법**: 라벨 검수 도구(`labeling-qa-tool/main.py`)로 `data/yolo`를 **읽기 전용 작업 공간**에 연결해 열람 (새 코드 없음)
> **작성**: 2026-10-13 · 최용훈

## 1. 확인 방법

- 작업 공간: `~/preview_ws/raw/yolo` ← `detection-model/data/yolo` 하드 링크 (`cp -al`) · 도구가 만드는 `manifests/`는 레포 밖 `~/preview_ws/`에 생김
- 도구에서 `raw`는 읽기 전용으로 취급 → 라벨 파일을 수정하지 않음 · 저장 · QA 버튼은 누르지 않음
- 확인 후 `~/preview_ws` 삭제 (원본 `data/yolo`는 그대로)

## 2. 확인 대상 (20장)

선정 규칙: 역할별 Class 0 · 1 · 2 · 3 · 5 · 6 각 1장 이상 → scene_type 각 1장 → 서로 다른 capture_group (무작위 아님)

| # | 역할 | 파일 | scene_type | 세션 | Class×개수 | 위치 · Class 일치 |
|---:|---|---|---|---|---|:-:|
| 1 | train | `250424_135756404426.jpg` | kimchi_with_target | G13 | 0×3 1×2 2×1 3×1 5×1 | ✅ |
| 2 | train | `250410_150040264734.jpg` | kimchi_with_target | G01-S5 | 6×5 | ✅ |
| 3 | train | `250513_014148760172.jpg` | object_only | G18 | 1×5 | ✅ |
| 4 | train | `250410_155526034625.jpg` | kimchi_with_target | G03 | 1×5 | ✅ |
| 5 | train | `250410_174241672560.jpg` | kimchi_with_target | G05 | 0×1 2×4 | ✅ |
| 6 | train | `250411_151707909443.jpg` | kimchi_with_target | G10 | 1×5 | ✅ |
| 7 | train | `250424_140721608012.jpg` | kimchi_with_target | G14 | 0×5 | ✅ |
| 8 | train | `250424_150320374794.jpg` | kimchi_with_target | G15 | 2×5 5×3 | ✅ |
| 9 | train | `250424_154322097228.jpg` | kimchi_with_target | G16 | 3×5 | ✅ |
| 10 | train | `250424_164033250654.jpg` | kimchi_with_target | G17 | 0×5 | ✅ |
| 11 | val | `250411_095845387065.jpg` | kimchi_with_target | G06 | 1×4 3×1 5×1 | ✅ |
| 12 | val | `250411_100243218238.jpg` | kimchi_with_target | G06 | 0×1 1×3 2×1 | ✅ |
| 13 | val | `250410_145804344533.jpg` | kimchi_with_target | G01-S4 | 6×5 | ✅ |
| 14 | val | `250411_140005265446.jpg` | kimchi_with_target | G09 | 1×8 | ✅ |
| 15 | val | `250411_092158458691.jpg` | kimchi_with_target | G06 | 1×5 | ✅ |
| 16 | test | `250424_112924042782.jpg` | kimchi_with_target | G11 | 0×1 1×2 2×2 3×2 5×1 | ✅ |
| 17 | test | `250410_144403911987.jpg` | kimchi_with_target | G01-S1 | 6×5 | ✅ |
| 18 | test | `250410_144834943618.jpg` | kimchi_with_target | G01-S2 | 5×1 6×5 | ✅ |
| 19 | test | `250411_133000176335.jpg` | kimchi_with_target | G08 | 1×5 | ✅ |
| 20 | test | `250410_144449962356.jpg` | kimchi_with_target | G01-S1 | 6×5 | ✅ |

- 커버리지: 세 역할 모두 Class 0 · 1 · 2 · 3 · 5 · 6 포함 · Train에 object_only 1장 포함
- Class 4는 Instance 0건 · normal_kimchi 0장 · Bridge는 data/yolo에 없어 대상 아님
- Test 5장은 **라벨 대응 확인만** 하고 모델 평가에는 쓰지 않음 (Frozen Test 원칙 유지)

## 3. 결과

- 확인: **20 / 20장 일치** (BBox 위치 · Class · 개수)
- 이상: 없음
- 09 자동 검증(라벨 원본과 바이트 동일 · 역할별 BBox 2,957 / 389 / 477)과 결론 일치
- 작업 공간 `~/preview_ws` 삭제 완료 · `data/yolo` 변경 없음
- 확인자 · 날짜: 최용훈 · 2026-10-13
