"""Split 단계: Split Freeze — splits/kimchi_v1_split.csv 를 확정본(manifests/)으로 얼린다.

사용법 (detection-model 폴더에서 실행):
    python scripts/06_freeze_split.py

결과:
    manifests/split_manifest.csv     900행 전체 · 스키마 v2 (최소 컬럼 · src/manifest.py)
    manifests/train.csv · val.csv · test.csv · bridge_holdout.csv
    ※ 10/13 Freeze 는 v1(3칸)으로 만들어졌고, upgrade_manifest_schema_v1_to_v2 로 v2 로 업그레이드했다 (배정 변경 0).
    reports/freeze_check.csv         Freeze 전 검사 결과 (item, expected, actual, result)

원칙:
    - 검사를 "모두" 통과해야만 manifests/ 를 만든다. 하나라도 FAIL 이면 아무 파일도 쓰지 않는다.
    - 이미 Freeze 되어 있으면 다시 쓰지 않는다. (같으면 확인만, 다르면 중단)
    - 기준값은 split_policy.md · README 에서 옮겨 적은 값이다. 실행 결과를 보고 고치지 않는다.
"""
from pathlib import Path
import csv
import hashlib
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.manifest import read_manifest, assignment, build_v2_rows, write_manifest_set, SPLIT_FILES

# ----------------------------------------------------------------------
# 경로
# ----------------------------------------------------------------------
SPLIT_CSV = PROJECT_ROOT / "splits" / "kimchi_v1_split.csv"
SRC_IMG = PROJECT_ROOT / "data" / "subject7_final" / "images"
SRC_LBL = PROJECT_ROOT / "data" / "subject7_final" / "labels"
MANIFEST_DIR = PROJECT_ROOT / "manifests"
STATS_CSV = PROJECT_ROOT / "reports" / "audit_label_stats.csv"   # source_dataset · original_split · scene_type
CHECK_CSV = PROJECT_ROOT / "reports" / "freeze_check.csv"

# ----------------------------------------------------------------------
# 기준값 (split_policy.md 1장 · 8장 / README 9장에서 옮겨 적은 값)
# ----------------------------------------------------------------------
LABEL_FP = "5c2b4fc2c3e6"           # kimchi_v1 라벨 지문 (README 6.1 명령과 같은 계산)
FROZEN_TEST_FP = "4f9291849fe6"     # Frozen Test 지문 (split_policy.md 8장)
EXPECTED_COUNTS = {"train": 600, "val": 74, "test": 80, "bridge": 146}   # 배정 결과 (8장)
TOTAL = 900
FIELDS = ["file_name", "capture_group", "role"]   # 입력 splits/kimchi_v1_split.csv 의 칸 (05 결과 · v1)



def fingerprint(names) -> str:
    """파일명 목록의 sha256 앞 12자리. 05_make_split.py 와 같은 방식."""
    text = "\n".join(sorted(names)).encode("utf-8")
    return hashlib.sha256(text).hexdigest()[:12]


def label_fingerprint(label_dir: Path) -> str:
    """라벨 지문. README 의 `LC_ALL=C cat labels/*.txt | sha256sum` 과 같은 값.
    LC_ALL=C 는 파일 이름을 '바이트 순서'로 정렬 → Python 에서는 이름을 bytes 로 정렬하면 같다."""
    h = hashlib.sha256()
    for p in sorted(label_dir.glob("*.txt"), key=lambda p: p.name.encode("utf-8")):
        h.update(p.read_bytes())                     # cat 처럼 파일 내용을 순서대로 이어 붙임
    return h.hexdigest()[:12]


def read_split(csv_path: Path) -> list[dict]:
    with open(csv_path, encoding="utf-8-sig", newline="") as f:     # utf-8-sig: 맨 앞 BOM 제거
        return list(csv.DictReader(f))


def main():
    if not SPLIT_CSV.exists():
        sys.exit(f"[중단] split 파일이 없습니다: {SPLIT_CSV}")
    rows = read_split(SPLIT_CSV)

    checks = []                                             # (item, expected, actual)

    def add(item, expected, actual):
        checks.append({"item": item, "expected": expected, "actual": actual,
                       "result": "PASS" if str(expected) == str(actual) else "FAIL"})

    # ① 형식: 칸 이름 · 행 수 · 중복 · 역할 이름 ------------------------------------
    add("columns", ",".join(FIELDS), ",".join(rows[0].keys()) if rows else "")
    add("rows", TOTAL, len(rows))
    names = [r["file_name"] for r in rows]
    add("duplicate_file_name", 0, len(names) - len(set(names)))
    add("unknown_role", 0, sum(r["role"] not in EXPECTED_COUNTS for r in rows))

    # ② 역할별 장수 (split_policy.md 8장 배정 결과) ---------------------------------
    for role, n in EXPECTED_COUNTS.items():
        add(f"count_{role}", n, sum(r["role"] == role for r in rows))

    # ③ Frozen Test 지문 ---------------------------------------------------------
    add("test_fingerprint", FROZEN_TEST_FP, fingerprint(r["file_name"] for r in rows if r["role"] == "test"))

    # ④ 한 세션(capture_group)은 한 역할에만 (Leakage 방지 · E1 하위 세션 기준) -------
    group_roles = {}
    for r in rows:
        group_roles.setdefault(r["capture_group"], set()).add(r["role"])
    add("group_in_multiple_roles", 0, sum(len(v) > 1 for v in group_roles.values()))

    # ⑤ 데이터와 짝이 맞는지: split 900장 = 실제 이미지 900장 · 라벨 지문 kimchi_v1 ------
    on_disk = {p.name for p in SRC_IMG.glob("*.jpg")}
    add("not_on_disk", 0, len(set(names) - on_disk))       # split 에는 있는데 이미지가 없음
    add("not_in_split", 0, len(on_disk - set(names)))      # 이미지는 있는데 split 에 없음
    add("label_fingerprint", LABEL_FP, label_fingerprint(SRC_LBL))

    # 검사 결과는 PASS/FAIL 과 상관없이 항상 저장 (실패 원인 추적용)
    CHECK_CSV.parent.mkdir(exist_ok=True)
    with open(CHECK_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "expected", "actual", "result"], lineterminator="\n")   # 줄바꿈 \n (기존 CSV 와 같게)
        writer.writeheader()
        writer.writerows(checks)

    print("=== Freeze 전 검사 ===")
    for c in checks:
        print(f"  {c['result']}  {c['item']:<24} 기대 {c['expected']} / 실제 {c['actual']}")
    n_fail = sum(c["result"] == "FAIL" for c in checks)
    print(f"  → PASS {len(checks) - n_fail} / FAIL {n_fail}   (저장: {CHECK_CSV.relative_to(PROJECT_ROOT)})")

    if n_fail:
        sys.exit("\n[중단] FAIL 이 있어 Freeze 하지 않았습니다. manifests/ 는 만들지 않았습니다.")

    # ⑥ 이미 Freeze 되어 있으면: 배정이 같으면 확인만, 다르면 중단 (얼린 것은 다시 쓰지 않는다) ---
    #    스키마(v1 3칸 · v2 9칸)와 상관없이 "누가 어느 역할인가"(배정)만 비교한다.
    full_path = MANIFEST_DIR / "split_manifest.csv"
    split_rows, _ = read_manifest(SPLIT_CSV)                          # role/bridge → split/bridge_holdout
    if full_path.exists():
        frozen, schema = read_manifest(full_path)
        if assignment(frozen) == assignment(split_rows):
            if schema == "v1":
                print("\n배정은 같지만 manifests/ 가 스키마 v1 입니다 → python scripts/archive/upgrade_manifest_schema_v1_to_v2.py")
            else:
                print("\n이미 Freeze 되어 있고 split 과 배정이 같습니다 (스키마 v2). 아무것도 다시 쓰지 않았습니다.")
            return
        sys.exit("\n[중단] 이미 Freeze 된 manifests/ 가 split 과 다릅니다. 팀 확인 전에는 덮어쓰지 않습니다.")

    # ⑦ Freeze: manifests/ 작성 (스키마 v2) -------------------------------------------
    with open(STATS_CSV, encoding="utf-8-sig", newline="") as f:
        stats = {r["file_name"]: r for r in csv.DictReader(f)}
    write_manifest_set(MANIFEST_DIR, build_v2_rows(split_rows, stats))   # 900행 · split 순서 그대로

    print("\n=== Freeze 완료 ===")
    for file_name in ["split_manifest.csv", *SPLIT_FILES.values()]:
        n = len(read_split(MANIFEST_DIR / file_name))
        print(f"  manifests/{file_name:<22} {n:>4}행")
    print(f"  Frozen Test 지문 {FROZEN_TEST_FP} · 라벨 지문 {LABEL_FP}")


if __name__ == "__main__":
    main()
