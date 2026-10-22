"""Split Manifest 읽기 · 쓰기 공통 기능.

manifest 스키마 v2 ("최소 컬럼"):
    file_name, image_path, label_path, source_dataset, original_split,
    scene_type, capture_group, split, dataset_version

split 값: train / val / test / bridge_holdout

v1 (2026-10-13 Freeze 당시) 은 file_name, capture_group, role 3칸이었고 Bridge 값이 "bridge" 였다.
read_manifest() 는 v1 · v2 · splits/kimchi_v1_split.csv 를 모두 읽어서
항상 split 키와 bridge_holdout 값으로 맞춰 돌려준다.
"""
from pathlib import Path
import csv
import hashlib

DATASET_VERSION = "kimchi_v1"
SPLITS = ["train", "val", "test", "bridge_holdout"]          # 요구사항 §11.3 의 split 값
YOLO_SPLITS = ["train", "val", "test"]                       # data/yolo · dataset.yaml 에 들어가는 역할
LEGACY_VALUES = {"bridge": "bridge_holdout"}                 # v1 값 → v2 값

MANIFEST_FIELDS = ["file_name", "image_path", "label_path", "source_dataset", "original_split",
                   "scene_type", "capture_group", "split", "dataset_version"]
SPLIT_FILES = {"train": "train.csv", "val": "val.csv", "test": "test.csv",
               "bridge_holdout": "bridge_holdout.csv"}

IMAGE_DIR = "data/subject7_final/images"                     # 프로젝트 루트(detection-model) 기준 상대경로
LABEL_DIR = "data/subject7_final/labels"


def normalize_split(value: str) -> str:
    """'bridge' 같은 v1 값을 v2 값으로 바꾼다. 모르는 값이면 그대로 둔다 (검사에서 걸리도록)."""
    return LEGACY_VALUES.get(value, value)


def schema_of(columns) -> str:
    """CSV 칸 이름을 보고 스키마 버전을 판단한다."""
    cols = list(columns)
    if cols == MANIFEST_FIELDS:
        return "v2"
    if cols[:3] == ["file_name", "capture_group", "role"]:
        return "v1"
    return "unknown"


def read_manifest(path: Path) -> tuple[list[dict], str]:
    """manifest(또는 split) CSV 를 읽어 (행 목록, 스키마) 를 돌려준다.
    모든 행에 file_name · capture_group · split 키가 있고, split 값은 v2 기준이다."""
    with open(path, encoding="utf-8-sig", newline="") as f:          # utf-8-sig: 맨 앞 BOM 제거
        reader = csv.DictReader(f)
        rows = list(reader)
        schema = schema_of(reader.fieldnames or [])
    if schema == "unknown":
        raise ValueError(f"{path.name}: 알 수 없는 칸 구성 {reader.fieldnames}")
    for r in rows:
        r["split"] = normalize_split(r["split"] if schema == "v2" else r["role"])
    return rows, schema


def assignment(rows: list[dict]) -> list[tuple]:
    """배정 비교용: (file_name, capture_group, split) 목록. 스키마가 달라도 배정이 같으면 같다."""
    return sorted((r["file_name"], r["capture_group"], r["split"]) for r in rows)


def build_v2_rows(rows: list[dict], stats: dict[str, dict]) -> list[dict]:
    """배정(file_name · capture_group · split)은 그대로 두고 v2 칸을 채운다.
    stats: reports/audit_label_stats.csv 를 file_name 으로 찾을 수 있게 만든 dict."""
    out = []
    for r in rows:
        s = stats[r["file_name"]]
        out.append({
            "file_name": r["file_name"],
            "image_path": f"{IMAGE_DIR}/{r['file_name']}",
            "label_path": f"{LABEL_DIR}/{Path(r['file_name']).stem}.txt",
            "source_dataset": s["source_dataset"],
            "original_split": s["original_split"],
            "scene_type": s["scene_type"],
            "capture_group": r["capture_group"],
            "split": r["split"],
            "dataset_version": DATASET_VERSION,
        })
    return out


def write_manifest_set(manifest_dir: Path, rows: list[dict]) -> None:
    """split_manifest.csv (900행) + 역할별 CSV 4개를 v2 스키마로 쓴다. 행 순서는 입력 순서 그대로."""
    manifest_dir.mkdir(exist_ok=True)

    def _write(path, part):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:   # 기존 CSV 와 같은 형식 (BOM · \n)
            writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows({k: r[k] for k in MANIFEST_FIELDS} for r in part)

    _write(manifest_dir / "split_manifest.csv", rows)
    for split, name in SPLIT_FILES.items():
        _write(manifest_dir / name, [r for r in rows if r["split"] == split])


def fingerprint(names) -> str:
    """파일명 목록의 sha256 앞 12자리 (05 · 06 · 08 · 09 와 같은 계산)."""
    text = "\n".join(sorted(names)).encode("utf-8")
    return hashlib.sha256(text).hexdigest()[:12]
