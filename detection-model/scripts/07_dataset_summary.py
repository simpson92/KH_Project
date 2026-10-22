"""Split 단계: 산출물 1 — reports/dataset_summary.csv (학습용 Dataset Version 요약표).

사용법 (detection-model 폴더에서 실행):
    python scripts/07_dataset_summary.py

입력 (모두 Git 에 있는 파일 · 이미지 불필요):
    manifests/split_manifest.csv      Freeze 된 역할 배정 (정답표)
    reports/audit_label_stats.csv     이미지별 BBox · Class 수 · scene_type (데이터 감사 단계 audit 결과)
    configs/dataset.yaml              YOLO 가 실제로 읽는 역할 (Bridge 포함 여부 확인)

결과:
    reports/dataset_summary.csv       역할 4개 + 합계 1행 (이미지 · 비율 · BBox · Class별 · 세션 · 날짜 · 장면 · yaml 포함 여부)

원칙: Split 단계 Daily Gate 의 산출물 1 항목을 검사하고, 모두 PASS 일 때만 요약표를 쓴다.
"""
from pathlib import Path
import csv
import sys

import yaml   # PyYAML (ultralytics 설치 시 함께 설치됨)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.manifest import read_manifest, SPLITS, DATASET_VERSION

# ----------------------------------------------------------------------
# 경로
# ----------------------------------------------------------------------
MANIFEST_CSV = PROJECT_ROOT / "manifests" / "split_manifest.csv"
STATS_CSV = PROJECT_ROOT / "reports" / "audit_label_stats.csv"
DATASET_YAML = PROJECT_ROOT / "configs" / "dataset.yaml"
OUT_CSV = PROJECT_ROOT / "reports" / "dataset_summary.csv"

# ----------------------------------------------------------------------
# 기준값 (split_policy.md · audit_expected.md v2 에서 옮겨 적은 값)
# ----------------------------------------------------------------------
ROLES = SPLITS                        # train · val · test · bridge_holdout
EXPECTED_TOTAL_IMAGES = 900
EXPECTED_TOTAL_BBOX = 4601            # kimchi_v1 (audit_expected.md v2 2장)
CLASSES = [f"class_{i}" for i in range(7)]


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    for p in (MANIFEST_CSV, STATS_CSV, DATASET_YAML):
        if not p.exists():
            sys.exit(f"[중단] 입력 파일이 없습니다: {p.relative_to(PROJECT_ROOT)}")

    manifest, schema = read_manifest(MANIFEST_CSV)                     # 항상 split 키 (v1 이면 role 을 변환)
    stats = {r["file_name"]: r for r in read_csv(STATS_CSV)}          # 파일명 → 이미지별 통계
    data_yaml = yaml.safe_load(DATASET_YAML.read_text(encoding="utf-8"))
    yaml_roles = {k for k in ("train", "val", "test") if data_yaml.get(k)}   # yaml 이 가리키는 역할
    yaml_paths = " ".join(str(data_yaml.get(k, "")) for k in ("train", "val", "test"))

    # ① 역할별 집계 -------------------------------------------------------------
    rows = []
    for role in ROLES:
        files = [r for r in manifest if r["split"] == role]
        st = [stats[r["file_name"]] for r in files if r["file_name"] in stats]
        row = {
            "split": role,
            "images": len(files),
            "ratio_pct": round(len(files) / EXPECTED_TOTAL_IMAGES * 100, 1),
            "bbox": sum(int(s["n_bbox"]) for s in st),
            **{c: sum(int(s[c]) for s in st) for c in CLASSES},
            "capture_groups": len({r["capture_group"] for r in files}),
            "dates": " ".join(sorted({r["file_name"][:6] for r in files})),          # 파일명 앞 6자리 = 촬영일
            "kimchi_with_target": sum(s["scene_type"] == "kimchi_with_target" for s in st),
            "object_only": sum(s["scene_type"] == "object_only" for s in st),
            "in_dataset_yaml": "yes" if role in yaml_roles else "no",
        }
        rows.append(row)

    total = {"split": "total"}
    for key in ["images", "ratio_pct", "bbox", *CLASSES, "capture_groups", "kimchi_with_target", "object_only"]:
        total[key] = round(sum(r[key] for r in rows), 1) if key == "ratio_pct" else sum(r[key] for r in rows)
    total["dates"] = " ".join(sorted({d for r in rows for d in r["dates"].split()}))
    total["in_dataset_yaml"] = "-"

    # ② Daily Gate 산출물 1 검사 --------------------------------------------------
    group_roles = {}
    for r in manifest:
        group_roles.setdefault(r["capture_group"], set()).add(r["split"])

    checks = [
        ("네 역할 수량의 합 = 900", EXPECTED_TOTAL_IMAGES, total["images"]),
        ("manifest 행 수 = 900", EXPECTED_TOTAL_IMAGES, len(manifest)),
        ("통계와 짝이 안 맞는 파일", 0, sum(r["file_name"] not in stats for r in manifest)),
        ("BBox 합계 = kimchi_v1", EXPECTED_TOTAL_BBOX, total["bbox"]),
        ("두 역할에 섞인 capture_group", 0, sum(len(v) > 1 for v in group_roles.values())),
        ("Bridge 가 dataset.yaml 에 포함", "no", "yes" if ("bridge" in yaml_roles or "bridge" in yaml_paths) else "no"),
        ("manifest 스키마", "v2", schema),
        ("Dataset Version", DATASET_VERSION, ",".join(sorted({r.get("dataset_version", "-") for r in manifest}))),
    ]
    print("=== 산출물 1 검사 (Split 단계 Daily Gate) ===")
    n_fail = 0
    for name, exp, act in checks:
        ok = str(exp) == str(act)
        n_fail += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<28} 기대 {exp} / 실제 {act}")
    if n_fail:
        sys.exit(f"\n[중단] FAIL {n_fail}건 → dataset_summary.csv 를 쓰지 않았습니다.")

    # ③ 저장 · 출력 ----------------------------------------------------------------
    fields = ["split", "images", "ratio_pct", "bbox", *CLASSES, "capture_groups", "dates",
              "kimchi_with_target", "object_only", "in_dataset_yaml"]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")   # 기존 CSV 와 같은 형식
        writer.writeheader()
        writer.writerows([*rows, total])

    print("\n=== reports/dataset_summary.csv ===")
    print(f"{'split':<15}{'images':>7}{'%':>6}{'bbox':>6}  {'c0':>4}{'c1':>5}{'c2':>4}{'c3':>4}{'c4':>3}{'c5':>4}{'c6':>4}  yaml")
    for r in [*rows, total]:
        print(f"{r['split']:<15}{r['images']:>7}{r['ratio_pct']:>6}{r['bbox']:>6}  "
              + "".join(f"{r[c]:>{w}}" for c, w in zip(CLASSES, [4, 5, 4, 4, 3, 4, 4]))
              + f"  {r['in_dataset_yaml']}")
    print(f"저장: {OUT_CSV.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
