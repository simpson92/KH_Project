"""Split 단계 보완: manifests/ 스키마 v1 → v2 ("최소 컬럼"). 배정은 한 장도 바꾸지 않는다.

사용법 (detection-model 폴더에서 실행):
    python scripts/archive/upgrade_manifest_schema_v1_to_v2.py

왜 필요한가:
    10/13 Freeze 때 manifests/ 는 file_name · capture_group · role 3칸이었다.
    요구사항 §16.1 은 image_path · label_path · source_dataset · original_split · scene_type ·
    capture_group · split · dataset_version 을 최소 컬럼으로 요구하고, split 값은 bridge_holdout 이다.

원칙 (기대값 v2 개정과 같은 절차):
    - 칸만 추가 · 이름만 맞춘다. 900장의 역할 배정은 그대로다.
    - 새 manifest 를 먼저 메모리에서 만들고 "불변 조건" 을 모두 검사한다.
      하나라도 FAIL 이면 아무 파일도 쓰지 않는다.
    - 이미 v2 이면 다시 쓰지 않고 확인만 한다.

결과:
    manifests/split_manifest.csv · train.csv · val.csv · test.csv · bridge_holdout.csv  (v2)
    reports/manifest_schema_check.csv                                                 (검사 결과)
"""
from pathlib import Path
import csv
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]   # scripts/archive/ 의 두 단계 위 = detection-model/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.manifest import (MANIFEST_FIELDS, SPLITS, DATASET_VERSION, read_manifest, assignment,
                          build_v2_rows, write_manifest_set, fingerprint)

MANIFEST_DIR = PROJECT_ROOT / "manifests"
SPLIT_CSV = PROJECT_ROOT / "splits" / "kimchi_v1_split.csv"
STATS_CSV = PROJECT_ROOT / "reports" / "audit_label_stats.csv"
CHECK_CSV = PROJECT_ROOT / "reports" / "manifest_schema_check.csv"

# 기준값 (split_policy.md 8장 · audit_expected.md v2 · 실행 결과를 보고 고치지 않음)
EXPECTED_COUNTS = {"train": 600, "val": 74, "test": 80, "bridge_holdout": 146}
FROZEN_TEST_FP = "4f9291849fe6"
TOTAL = 900
SCENE_TOTALS = {"kimchi_with_target": 750, "object_only": 150}   # audit_expected.md 3장


def main():
    full_path = MANIFEST_DIR / "split_manifest.csv"
    for p in (full_path, SPLIT_CSV, STATS_CSV):
        if not p.exists():
            sys.exit(f"[중단] 입력 파일이 없습니다: {p.relative_to(PROJECT_ROOT)}")

    old_rows, schema = read_manifest(full_path)
    split_rows, _ = read_manifest(SPLIT_CSV)
    with open(STATS_CSV, encoding="utf-8-sig", newline="") as f:
        stats = {r["file_name"]: r for r in csv.DictReader(f)}

    print(f"현재 manifests/ 스키마: {schema}")
    missing_stats = [r["file_name"] for r in old_rows if r["file_name"] not in stats]
    if missing_stats:
        sys.exit(f"[중단] audit_label_stats 에 없는 파일 {len(missing_stats)}개 (예: {missing_stats[:2]})")

    new_rows = build_v2_rows(old_rows, stats)            # 행 순서 · 배정 그대로, 칸만 채움

    # ① 불변 조건 검사 ---------------------------------------------------------------
    checks = []

    def add(item, expected, actual):
        checks.append({"item": item, "expected": expected, "actual": actual,
                       "result": "PASS" if str(expected) == str(actual) else "FAIL"})

    add("rows", TOTAL, len(new_rows))
    add("assignment_same_as_old_manifest", "yes", "yes" if assignment(new_rows) == assignment(old_rows) else "no")
    add("assignment_same_as_split_csv", "yes", "yes" if assignment(new_rows) == assignment(split_rows) else "no")
    add("unknown_split_value", 0, sum(r["split"] not in SPLITS for r in new_rows))
    for split, n in EXPECTED_COUNTS.items():
        add(f"count_{split}", n, sum(r["split"] == split for r in new_rows))
    add("test_fingerprint", FROZEN_TEST_FP, fingerprint(r["file_name"] for r in new_rows if r["split"] == "test"))
    groups = {}
    for r in new_rows:
        groups.setdefault(r["capture_group"], set()).add(r["split"])
    add("group_in_multiple_splits", 0, sum(len(v) > 1 for v in groups.values()))
    for scene, n in SCENE_TOTALS.items():
        add(f"scene_{scene}", n, sum(r["scene_type"] == scene for r in new_rows))
    add("dataset_version", DATASET_VERSION, ",".join(sorted({r["dataset_version"] for r in new_rows})))
    add("path_matches_file_name", 0,
        sum(not (r["image_path"].endswith("/" + r["file_name"])
                 and Path(r["label_path"]).stem == Path(r["file_name"]).stem) for r in new_rows))

    CHECK_CSV.parent.mkdir(exist_ok=True)
    with open(CHECK_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "expected", "actual", "result"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(checks)

    print("\n=== 스키마 업그레이드 불변 조건 검사 ===")
    for c in checks:
        print(f"  {c['result']}  {c['item']:<34} 기대 {c['expected']} / 실제 {c['actual']}")
    n_fail = sum(c["result"] == "FAIL" for c in checks)
    print(f"  → PASS {len(checks) - n_fail} / FAIL {n_fail}   (저장: {CHECK_CSV.relative_to(PROJECT_ROOT)})")
    if n_fail:
        sys.exit("\n[중단] FAIL 이 있어 manifests/ 를 바꾸지 않았습니다.")

    # ② 이미 v2 면 다시 쓰지 않음 (확인만) --------------------------------------------
    if schema == "v2":
        same = [{k: r[k] for k in MANIFEST_FIELDS} for r in old_rows] == new_rows
        print("\n이미 v2 입니다. " + ("내용도 같아서 아무것도 다시 쓰지 않았습니다." if same
                                    else "[주의] 내용이 다릅니다 → 팀 확인 전에는 덮어쓰지 않습니다."))
        return

    # ③ v1 → v2 쓰기 -------------------------------------------------------------------
    write_manifest_set(MANIFEST_DIR, new_rows)
    print("\n=== manifests/ v1 → v2 완료 (배정 변경 0) ===")
    for name in ["split_manifest.csv", "train.csv", "val.csv", "test.csv", "bridge_holdout.csv"]:
        rows, sch = read_manifest(MANIFEST_DIR / name)
        print(f"  manifests/{name:<22} {len(rows):>4}행 · {sch}")


if __name__ == "__main__":
    main()
