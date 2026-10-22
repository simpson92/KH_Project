"""Split 단계: Split 목록 → YOLO 학습 폴더(data/yolo) 구성.

사용법 (detection-model 폴더에서 실행):
    python scripts/08_build_yolo_dataset.py --from-split    # ① 리허설: splits/kimchi_v1_split.csv 사용 (Freeze 전)
    python scripts/08_build_yolo_dataset.py --overwrite     # ② 본 실행: manifests/split_manifest.csv 사용 (Freeze 후)

결과:
    data/yolo/images/{train,val,test}/*.jpg   (Git 제외 · NDA)
    data/yolo/labels/{train,val,test}/*.txt   (Git 제외 · NDA)
    reports/yolo_build_summary.csv            (역할별 이미지 · 라벨 · BBox 수 · Test 지문)

원칙:
    - 원본(data/subject7_final)은 읽기만 한다. 복사(copy)만 하고 이동 · 이름 변경은 하지 않는다.
    - Bridge Holdout은 data/yolo에 넣지 않는다. (검출 모델 단계 사용 금지 → 실수할 길을 아예 막음)
    - 검사(누락 · 지문)를 모두 통과한 뒤에만 복사를 시작한다.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]          # scripts/ 한 단계 위 = detection-model/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.manifest import read_manifest, SPLITS     # manifest v1 · v2 · split CSV 를 같은 모양(split 키)으로 읽기

# ----------------------------------------------------------------------
# 경로
# ----------------------------------------------------------------------
SRC_IMG = PROJECT_ROOT / "data" / "subject7_final" / "images"
SRC_LBL = PROJECT_ROOT / "data" / "subject7_final" / "labels"
SPLIT_CSV = PROJECT_ROOT / "splits" / "kimchi_v1_split.csv"         # Freeze 전 (리허설용)
MANIFEST_CSV = PROJECT_ROOT / "manifests" / "split_manifest.csv"    # Freeze 후 (본 실행용)
OUT_DIR = PROJECT_ROOT / "data" / "yolo"                            # configs/dataset.yaml 의 path
SUMMARY_CSV = PROJECT_ROOT / "reports" / "yolo_build_summary.csv"

# ----------------------------------------------------------------------
# 기준값 (split_policy.md · README 9장에서 옮겨 적은 값 · 실행 결과를 보고 고치지 않음)
# ----------------------------------------------------------------------
YOLO_ROLES = ["train", "val", "test"]       # data/yolo 에 넣는 역할 (bridge_holdout 제외)
ALL_ROLES = set(SPLITS)                     # train · val · test · bridge_holdout
FROZEN_TEST_FP = "4f9291849fe6"             # Frozen Test 지문 (split_policy.md 8장)


def fingerprint(names) -> str:
    """파일명 목록의 sha256 앞 12자리. 05_make_split.py 와 '완전히 같은' 방식이어야 비교가 의미 있다."""
    text = "\n".join(sorted(names)).encode("utf-8")   # 정렬 → 순서와 무관
    return hashlib.sha256(text).hexdigest()[:12]


def load_rows(csv_path: Path) -> list[dict]:
    """split / manifest CSV 읽기 + 형식 검사 (칸 이름 · 역할 이름 · 중복)."""
    try:
        rows, _ = read_manifest(csv_path)       # 모든 행에 split 키 (v1 의 role · bridge 는 split · bridge_holdout 로)
    except (ValueError, KeyError) as e:
        sys.exit(f"[중단] {csv_path.name} 칸 구성이 다릅니다: {e}")

    bad_roles = {r["split"] for r in rows} - ALL_ROLES
    if bad_roles:
        sys.exit(f"[중단] 알 수 없는 split 값: {bad_roles}")

    names = [r["file_name"] for r in rows]
    if len(names) != len(set(names)):
        sys.exit("[중단] 같은 file_name 이 두 번 이상 나옵니다 (한 장이 두 역할에 배정됨).")
    return rows


def count_bbox(label_path: Path) -> int:
    """YOLO 라벨 1개 파일의 BBox 수 = 비어 있지 않은 줄 수."""
    with open(label_path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def main():
    parser = argparse.ArgumentParser(description="Split 목록으로 data/yolo 폴더 구성")
    parser.add_argument("--from-split", action="store_true",
                        help="Freeze 전 리허설: manifests 대신 splits/kimchi_v1_split.csv 사용")
    parser.add_argument("--overwrite", action="store_true",
                        help="data/yolo 가 이미 있으면 지우고 다시 만듦")
    args = parser.parse_args()

    # ① 입력 고르기 ---------------------------------------------------------
    src_csv = SPLIT_CSV if args.from_split else MANIFEST_CSV
    if not src_csv.exists():
        hint = "" if args.from_split else "\n       아직 Freeze 전이면 --from-split 으로 리허설하세요."
        sys.exit(f"[중단] 입력 파일이 없습니다: {src_csv}{hint}")
    print(f"입력: {src_csv.relative_to(PROJECT_ROOT)}  ({'리허설' if args.from_split else '본 실행'})")

    rows = load_rows(src_csv)
    by_role = {role: [r["file_name"] for r in rows if r["split"] == role] for role in ALL_ROLES}

    # ② 검사 1: Frozen Test 지문 (다르면 아무것도 복사하지 않음) -----------------
    test_fp = fingerprint(by_role["test"])
    if test_fp != FROZEN_TEST_FP:
        sys.exit(f"[중단] Frozen Test 지문 불일치: {test_fp} (기대 {FROZEN_TEST_FP})")
    print(f"검사 1  Frozen Test 지문 {test_fp} 일치")

    # ③ 검사 2: 복사할 원본이 전부 있는지 (하나라도 없으면 복사 전에 멈춤) ----------
    missing = []
    for role in YOLO_ROLES:
        for name in by_role[role]:
            if not (SRC_IMG / name).exists():
                missing.append(f"images/{name}")
            if not (SRC_LBL / f"{Path(name).stem}.txt").exists():
                missing.append(f"labels/{Path(name).stem}.txt")
    if missing:
        sys.exit(f"[중단] 원본 누락 {len(missing)}건 (예: {missing[:3]})")
    print(f"검사 2  원본 누락 0건 ({sum(len(by_role[r]) for r in YOLO_ROLES)}쌍)")

    # ④ 출력 폴더 준비 -------------------------------------------------------
    if OUT_DIR.exists() and any(OUT_DIR.iterdir()):
        if not args.overwrite:
            sys.exit(f"[중단] {OUT_DIR.relative_to(PROJECT_ROOT)} 가 이미 있습니다. 다시 만들려면 --overwrite")
        # 안전장치: 지우는 대상이 정확히 detection-model/data/yolo 인지 한 번 더 확인
        assert OUT_DIR.resolve() == (PROJECT_ROOT / "data" / "yolo").resolve()
        shutil.rmtree(OUT_DIR)
        print("기존 data/yolo 삭제 (--overwrite)")

    # ⑤ 복사 (원본 → data/yolo/images|labels/<role>/) -------------------------
    summary = []
    for role in YOLO_ROLES:
        img_dir = OUT_DIR / "images" / role
        lbl_dir = OUT_DIR / "labels" / role         # Ultralytics 는 경로의 images → labels 로 바꿔 라벨을 찾음
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        n_bbox = 0
        for name in by_role[role]:
            stem = Path(name).stem
            shutil.copy2(SRC_IMG / name, img_dir / name)                 # copy2: 수정 시각도 보존
            shutil.copy2(SRC_LBL / f"{stem}.txt", lbl_dir / f"{stem}.txt")
            n_bbox += count_bbox(lbl_dir / f"{stem}.txt")

        summary.append({
            "role": role,
            "images": len(list(img_dir.glob("*.jpg"))),
            "labels": len(list(lbl_dir.glob("*.txt"))),
            "bbox": n_bbox,
            "fingerprint": fingerprint(p.name for p in img_dir.glob("*.jpg")),
        })

    # ⑥ 검사 3: 복사 결과 확인 --------------------------------------------------
    problems = []
    for s in summary:
        expected = len(by_role[s["role"]])
        if not (s["images"] == s["labels"] == expected):
            problems.append(f"{s['role']}: 이미지 {s['images']} / 라벨 {s['labels']} / 기대 {expected}")
    copied = {p.name for p in (OUT_DIR / "images").rglob("*.jpg")}
    leaked = copied & set(by_role["bridge_holdout"])
    if leaked:
        problems.append(f"Bridge 이미지가 data/yolo 에 들어감: {len(leaked)}장")
    test_row = next(s for s in summary if s["role"] == "test")
    if test_row["fingerprint"] != FROZEN_TEST_FP:
        problems.append(f"복사된 Test 지문 불일치: {test_row['fingerprint']}")

    # ⑦ 결과 저장 · 출력 ----------------------------------------------------------
    SUMMARY_CSV.parent.mkdir(exist_ok=True)
    with open(SUMMARY_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["role", "images", "labels", "bbox", "fingerprint"], lineterminator="\n")   # 줄바꿈 \n (기존 CSV 와 같게)
        writer.writeheader()
        writer.writerows(summary)

    print("\n=== data/yolo 구성 결과 ===")
    print(f"{'role':<6} {'images':>6} {'labels':>6} {'bbox':>6}  fingerprint")
    for s in summary:
        print(f"{s['role']:<6} {s['images']:>6} {s['labels']:>6} {s['bbox']:>6}  {s['fingerprint']}")
    print(f"bridge_holdout {len(by_role['bridge_holdout'])}장 → data/yolo 미포함 (검출 모델 단계 사용 금지)")
    print(f"저장: {SUMMARY_CSV.relative_to(PROJECT_ROOT)}")

    if problems:
        print("\n[FAIL] 검사 3 문제:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("\n검사 3  개수 · Bridge 미포함 · Test 지문 → PASS")


if __name__ == "__main__":
    main()
