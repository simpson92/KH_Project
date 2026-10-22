"""Dataset Audit 기능 모음.

학습 전에 데이터가 정상인지 "건강검진"하는 함수들입니다.
라벨을 고치지 않고, 읽기만 해서 문제를 목록으로 남깁니다.

    입력  : 이미지 폴더 + YOLO TXT 폴더 (+ 라벨 검수 단계 Manifest)
    처리  : Pair / YOLO 형식 / Class / 좌표 / 분포 확인
    출력  : 문제 목록(issues) + 통계(stats)
"""
from collections import Counter
from pathlib import Path
import csv

# ----------------------------------------------------------------------
# 라벨 검수 단계 기준 (바꾸지 않음)
# ----------------------------------------------------------------------
VALID_CLASSES = range(0, 7)        # Class ID 0~6
UNUSED_CLASSES = {4}               # Class 4 고무장갑: 사용하지 않음
IMAGE_EXTS = {".jpg", ".jpeg"}     # 대소문자 상관없이 비교 (.JPG 포함)
EPS = 1e-6                         # 소수점 반올림 오차 허용 범위

# 문제 종류별 심각도
#   ERROR : 학습 전에 반드시 원인을 확인해야 하는 문제
#   WARN  : 오류로 단정하지 않고 사람이 확인할 항목
SEVERITY = {
    "MISSING_LABEL": "ERROR",        # 이미지는 있는데 TXT 없음
    "MISSING_IMAGE": "ERROR",        # TXT는 있는데 이미지 없음
    "COLUMN_COUNT": "ERROR",         # 한 줄이 5칸이 아님
    "PARSE_ERROR": "ERROR",          # 숫자로 읽을 수 없음
    "CLASS_RANGE": "ERROR",          # Class ID가 0~6 밖
    "CENTER_RANGE": "ERROR",         # 중심 좌표가 0~1 밖
    "SIZE_RANGE": "ERROR",           # 너비/높이가 0 이하 또는 1 초과
    "BBOX_OUT_OF_IMAGE": "ERROR",    # 박스가 이미지 경계를 넘어감
    "NOT_IN_MANIFEST": "ERROR",      # 이미지가 Manifest에 없음
    "MISSING_IN_DATASET": "ERROR",   # Manifest에는 있는데 이미지가 없음
    "EMPTY_LABEL": "WARN",           # 빈 TXT (Negative Sample인지 확인)
    "CLASS4_REVIEW": "WARN",         # 사용하지 않는 Class 4 발견
}


def validate_yolo_row(row: str) -> list[str]:
    """YOLO TXT 한 줄을 검사해서 문제 종류 목록을 돌려준다. 문제 없으면 []."""
    parts = row.strip().split()

    # 1) 칸 수: class x y w h = 5칸
    if len(parts) != 5:
        return ["COLUMN_COUNT"]

    # 2) 숫자 변환: class는 정수, 나머지는 실수
    try:
        cls = int(parts[0])
        x, y, w, h = map(float, parts[1:])
    except ValueError:
        return ["PARSE_ERROR"]

    issues = []

    # 3) Class 범위
    if cls not in VALID_CLASSES:
        issues.append("CLASS_RANGE")
    elif cls in UNUSED_CLASSES:
        issues.append("CLASS4_REVIEW")

    # 4) 좌표 범위 (정규화 좌표라 0~1 이어야 함)
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        issues.append("CENTER_RANGE")
    if not (0.0 < w <= 1.0 and 0.0 < h <= 1.0):
        issues.append("SIZE_RANGE")

    # 5) 박스 경계: 중심 ± 절반 크기가 이미지 안에 있어야 함
    #    (좌표 범위 오류가 없을 때만 확인해서 같은 문제를 두 번 세지 않음)
    if "CENTER_RANGE" not in issues and "SIZE_RANGE" not in issues:
        left, right = x - w / 2, x + w / 2
        top, bottom = y - h / 2, y + h / 2
        if left < -EPS or top < -EPS or right > 1 + EPS or bottom > 1 + EPS:
            issues.append("BBOX_OUT_OF_IMAGE")

    return issues


def _issue(file: str, issue_type: str, line: int | str = "", detail: str = "") -> dict:
    """문제 한 건을 CSV 한 줄 형태(dict)로 만든다."""
    return {
        "file": file,
        "line": line,
        "issue_type": issue_type,
        "severity": SEVERITY.get(issue_type, "ERROR"),
        "detail": detail,
    }


def read_manifest(manifest_path: Path) -> dict[str, dict]:
    """라벨 검수 단계 Manifest를 읽어 {파일명: 행} 으로 돌려준다. (BOM 있어도 읽힘)"""
    with open(manifest_path, encoding="utf-8-sig", newline="") as f:
        return {row["file_name"]: row for row in csv.DictReader(f)}


def audit_dataset(images_dir: Path, labels_dir: Path, manifest_path: Path | None = None):
    """폴더 전체를 검사한다.

    Returns:
        issues      : 문제 목록 (dict 리스트)
        stats       : 전체 통계 (dict)
        image_rows  : 이미지별 BBox 통계 (3번 분포 분석용)
    """
    images_dir, labels_dir = Path(images_dir), Path(labels_dir)

    # 입력 폴더가 실제로 있는지 먼저 확인 (경로 오류를 가장 먼저 잡기)
    for d in (images_dir, labels_dir):
        if not d.is_dir():
            raise FileNotFoundError(f"폴더를 찾을 수 없습니다: {d}")

    # ① 이미지 / TXT 목록 읽기 (파일명에서 확장자를 뺀 stem 기준으로 짝을 맞춤)
    images = {p.stem: p for p in images_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS}
    labels = {p.stem: p for p in labels_dir.iterdir() if p.suffix.lower() == ".txt"}

    issues: list[dict] = []

    # ② JPG ↔ TXT Pair 확인
    for stem in sorted(images.keys() - labels.keys()):
        issues.append(_issue(images[stem].name, "MISSING_LABEL", detail="같은 이름의 TXT 없음"))
    for stem in sorted(labels.keys() - images.keys()):
        issues.append(_issue(labels[stem].name, "MISSING_IMAGE", detail="같은 이름의 이미지 없음"))
    pairs = sorted(images.keys() & labels.keys())

    # ③ TXT 한 줄씩 검사 + Class별 개수 세기
    class_counts: Counter = Counter()
    image_rows: list[dict] = []
    for stem in pairs:
        txt = labels[stem]
        lines = [ln for ln in txt.read_text(encoding="utf-8").splitlines() if ln.strip()]

        if not lines:  # 빈 TXT: 오류로 단정하지 않고 확인 항목으로 남김
            issues.append(_issue(txt.name, "EMPTY_LABEL", detail="BBox 0개"))

        per_image: Counter = Counter()
        for no, line in enumerate(lines, start=1):
            problems = validate_yolo_row(line)
            for p in problems:
                issues.append(_issue(txt.name, p, line=no, detail=line.strip()))
            # 형식이 읽히고 Class가 0~6인 줄만 Class 개수에 포함
            # (그래야 bbox_total = class_0 ~ class_6 의 합이 됨)
            if not ({"COLUMN_COUNT", "PARSE_ERROR", "CLASS_RANGE"} & set(problems)):
                cls = int(line.split()[0])
                class_counts[cls] += 1
                per_image[cls] += 1

        row = {"file_name": images[stem].name, "n_bbox": sum(per_image.values())}
        for c in VALID_CLASSES:
            row[f"class_{c}"] = per_image.get(c, 0)
        image_rows.append(row)

    # ④ Manifest 대조 (있을 때만)
    manifest = None
    if manifest_path is not None:
        manifest = read_manifest(Path(manifest_path))
        image_names = {p.name for p in images.values()}
        for name in sorted(image_names - manifest.keys()):
            issues.append(_issue(name, "NOT_IN_MANIFEST"))
        for name in sorted(manifest.keys() - image_names):
            issues.append(_issue(name, "MISSING_IN_DATASET"))
        # 이미지별 통계에 출처 · split · scene_type 붙이기 (3번 분석용)
        for row in image_rows:
            m = manifest.get(row["file_name"], {})
            row["source_dataset"] = m.get("source_dataset", "")
            row["original_split"] = m.get("original_split", "")
            row["scene_type"] = m.get("scene_type", "")

    # ⑤ 통계 정리
    issue_counts = Counter(i["issue_type"] for i in issues)
    format_types = {"COLUMN_COUNT", "PARSE_ERROR", "CLASS_RANGE",
                    "CENTER_RANGE", "SIZE_RANGE", "BBOX_OUT_OF_IMAGE"}
    n_bbox = [r["n_bbox"] for r in image_rows]
    stats = {
        "jpg_count": len(images),
        "txt_count": len(labels),
        "pair_count": len(pairs),
        "missing_label": issue_counts["MISSING_LABEL"],
        "missing_image": issue_counts["MISSING_IMAGE"],
        "empty_label": issue_counts["EMPTY_LABEL"],
        # Class 4는 "줄 수"가 아니라 "Class 4가 들어 있는 TXT 파일 수"로 셈 (기대값 메모 기준)
        "class4_files": len({i["file"] for i in issues if i["issue_type"] == "CLASS4_REVIEW"}),
        "format_errors": sum(issue_counts[t] for t in format_types),
        "bbox_total": sum(class_counts.values()),
        "bbox_per_image_min": min(n_bbox) if n_bbox else 0,
        "bbox_per_image_max": max(n_bbox) if n_bbox else 0,
        "bbox_per_image_mean": round(sum(n_bbox) / len(n_bbox), 2) if n_bbox else 0,
    }
    for c in VALID_CLASSES:
        stats[f"class_{c}"] = class_counts.get(c, 0)
    if manifest is not None:
        stats["manifest_rows"] = len(manifest)
        stats["not_in_manifest"] = issue_counts["NOT_IN_MANIFEST"]
        stats["missing_in_dataset"] = issue_counts["MISSING_IN_DATASET"]

    return issues, stats, image_rows


def compare_with_expected(stats: dict, expected: dict) -> list[dict]:
    """기대값과 실제값을 항목별로 비교한다. (테스트의 Expected vs Actual)"""
    rows = []
    for key, exp in expected.items():
        act = stats.get(key, "N/A")
        rows.append({"item": key, "expected": exp, "actual": act,
                     "result": "PASS" if act == exp else "FAIL"})
    return rows


def write_csv(rows: list[dict], path: Path, fieldnames: list[str]) -> None:
    """dict 리스트를 CSV로 저장한다. 엑셀에서 한글이 깨지지 않게 utf-8-sig 사용."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
