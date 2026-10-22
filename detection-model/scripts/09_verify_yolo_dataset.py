"""Split 단계: data/yolo 검증 — B 가 만든 YOLO 학습 폴더가 Freeze 된 manifests 와 정확히 같은지 확인한다.

사용법 (detection-model 폴더에서 실행):
    python scripts/09_verify_yolo_dataset.py

결과:
    reports/yolo_verify_check.csv    검증 항목별 기대값 · 실제값 · PASS/FAIL
    종료 코드                          모두 PASS → 0 / 하나라도 FAIL → 1

원칙:
    - 만든 사람(B · 08)과 검사하는 사람(A · 09)을 나눈다. 09 는 08 의 코드를 import 하지 않는다.
    - data/yolo 는 읽기만 한다. 고치지 않는다. (문제가 있으면 원인을 찾고 08 을 다시 돌린다)
    - 기준값은 manifests/ · split_policy.md · reports/split_summary.csv(데이터 감사 단계)에서 옮겨 적은 값이다.
"""
from pathlib import Path
import csv
import hashlib
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]          # scripts/ 한 단계 위 = detection-model/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.manifest import read_manifest   # manifest 읽기만 공유 (08 의 구성 코드는 여전히 import 하지 않음)

# ----------------------------------------------------------------------
# 경로
# ----------------------------------------------------------------------
MANIFEST_CSV = PROJECT_ROOT / "manifests" / "split_manifest.csv"
SRC_LBL = PROJECT_ROOT / "data" / "subject7_final" / "labels"
YOLO_DIR = PROJECT_ROOT / "data" / "yolo"
CHECK_CSV = PROJECT_ROOT / "reports" / "yolo_verify_check.csv"

# ----------------------------------------------------------------------
# 기준값 (실행 결과를 보고 고치지 않음)
# ----------------------------------------------------------------------
YOLO_ROLES = ["train", "val", "test"]                        # bridge 는 data/yolo 에 없어야 함
EXPECTED_IMAGES = {"train": 600, "val": 74, "test": 80}      # split_policy.md 8장
EXPECTED_BBOX = {"train": 2957, "val": 389, "test": 477}     # reports/split_summary.csv (데이터 감사 단계)
FROZEN_TEST_FP = "4f9291849fe6"                              # split_policy.md 8장


def fingerprint(names) -> str:
    """파일명 목록의 sha256 앞 12자리 (05 · 06 · 08 과 같은 계산)."""
    text = "\n".join(sorted(names)).encode("utf-8")
    return hashlib.sha256(text).hexdigest()[:12]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def count_bbox(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def main():
    # 0. 전제 조건: 검사할 대상과 기준이 있어야 함 -------------------------------------
    if not MANIFEST_CSV.exists():
        sys.exit(f"[중단] manifests 가 없습니다 (Freeze 전): {MANIFEST_CSV}")
    if not YOLO_DIR.exists():
        sys.exit(f"[중단] data/yolo 가 없습니다. B 의 08 본 실행이 끝났는지 확인하세요.")

    manifest, _ = read_manifest(MANIFEST_CSV)                        # 항상 split 키 · bridge_holdout 값
    role_of = {r["file_name"]: r["split"] for r in manifest}         # 파일명 → 역할 (정답표)
    stem_role = {Path(k).stem: v for k, v in role_of.items()}
    bridge = {k for k, v in role_of.items() if v == "bridge_holdout"}

    checks = []

    def add(no, item, expected, actual):
        checks.append({"no": no, "item": item, "expected": expected, "actual": actual,
                       "result": "PASS" if str(expected) == str(actual) else "FAIL"})

    # 실제 폴더 내용 읽기 (역할별 이미지 · 라벨 이름 목록)
    images = {role: sorted(p.name for p in (YOLO_DIR / "images" / role).glob("*.jpg")) for role in YOLO_ROLES}
    labels = {role: sorted(p.name for p in (YOLO_DIR / "labels" / role).glob("*.txt")) for role in YOLO_ROLES}

    # 1. 역할별 이미지 수 · 라벨 수 · 짝 ------------------------------------------------
    for role in YOLO_ROLES:
        add(1, f"{role}_images", EXPECTED_IMAGES[role], len(images[role]))
        add(1, f"{role}_labels", EXPECTED_IMAGES[role], len(labels[role]))
        unpaired = {Path(n).stem for n in images[role]} ^ {Path(n).stem for n in labels[role]}
        add(1, f"{role}_unpaired", 0, len(unpaired))                 # ^ = 한쪽에만 있는 이름

    # 2. Frozen Test 지문 (복사된 test 폴더 기준) --------------------------------------
    add(2, "test_fingerprint", FROZEN_TEST_FP, fingerprint(images["test"]))

    # 3. Bridge 미포함 · data/yolo 의 모든 jpg 가 정확한 역할 폴더에 있음 ------------------
    all_jpg = list((YOLO_DIR / "images").rglob("*.jpg"))
    add(3, "bridge_in_yolo", 0, sum(p.name in bridge for p in all_jpg))
    add(3, "not_in_manifest", 0, sum(p.name not in role_of for p in all_jpg))
    add(3, "wrong_role_folder", 0, sum(p.parent.name != role_of.get(p.name, p.parent.name) for p in all_jpg))
    extra_dirs = sorted(p.name for p in (YOLO_DIR / "images").iterdir() if p.is_dir() and p.name not in YOLO_ROLES)
    add(3, "extra_role_dirs", "-", ",".join(extra_dirs) or "-")      # bridge/ 같은 폴더가 있으면 FAIL

    # 4. 라벨 내용이 원본(subject7_final)과 바이트 단위로 같음 -----------------------------
    changed = 0
    for role in YOLO_ROLES:
        for name in labels[role]:
            src = SRC_LBL / name
            if not src.exists() or file_hash(src) != file_hash(YOLO_DIR / "labels" / role / name):
                changed += 1
    add(4, "label_changed_vs_source", 0, changed)

    # 5. 역할별 BBox 합계 (데이터 감사 단계 split_summary.csv 와 같아야 함) --------------------------
    for role in YOLO_ROLES:
        total = sum(count_bbox(YOLO_DIR / "labels" / role / n) for n in labels[role])
        add(5, f"{role}_bbox", EXPECTED_BBOX[role], total)

    # 6. 한 세션이 두 역할에 걸치지 않음 (manifest 기준 재확인) ---------------------------
    group_roles = {}
    for r in manifest:
        group_roles.setdefault(r["capture_group"], set()).add(r["split"])
    add(6, "group_in_multiple_roles", 0, sum(len(v) > 1 for v in group_roles.values()))

    # 저장 · 출력 ------------------------------------------------------------------
    CHECK_CSV.parent.mkdir(exist_ok=True)
    with open(CHECK_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["no", "item", "expected", "actual", "result"], lineterminator="\n")   # 줄바꿈 \n (기존 CSV 와 같게)
        writer.writeheader()
        writer.writerows(checks)

    print("=== data/yolo 검증 (manifests 기준) ===")
    for c in checks:
        print(f"  {c['result']}  {c['no']}. {c['item']:<24} 기대 {c['expected']} / 실제 {c['actual']}")
    n_fail = sum(c["result"] == "FAIL" for c in checks)
    print(f"  → PASS {len(checks) - n_fail} / FAIL {n_fail}   (저장: {CHECK_CSV.relative_to(PROJECT_ROOT)})")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
