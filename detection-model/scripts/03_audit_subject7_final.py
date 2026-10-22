"""데이터 감사 단계: 검수 완료 데이터셋 Dataset Audit 실행.

사용법 (detection-model 폴더에서 실행):
    python scripts/03_audit_subject7_final.py --fixture   # ① 작은 테스트 (일부러 망가뜨린 데이터)
    python scripts/03_audit_subject7_final.py             # ② 900장 전체

결과:
    --fixture : data/audit_test/audit_issue.csv          (Git 제외 · 테스트용)
    전체      : reports/audit_issue.csv                 (발견된 문제 목록)
                reports/audit_check.csv                 (기대값 vs 실제값)
                reports/audit_label_stats.csv           (이미지별 BBox 수 · 3번 분포 분석용)
"""
from pathlib import Path
import argparse
import sys

# 이 파일 위치(scripts/)의 한 단계 위 = 프로젝트 루트(detection-model/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset_audit import audit_dataset, compare_with_expected, write_csv, VALID_CLASSES

# ----------------------------------------------------------------------
# 경로
# ----------------------------------------------------------------------
FINAL_DIR = PROJECT_ROOT / "data" / "subject7_final"
FIXTURE_DIR = PROJECT_ROOT / "data" / "audit_test"
MANIFEST = PROJECT_ROOT.parent / "labeling-qa-tool" / "manifests" / "dataset_manifest.csv"
REPORT_DIR = PROJECT_ROOT / "reports"

# ----------------------------------------------------------------------
# 기대값: reports/audit_expected.md v2 1·2장에서 옮겨 적은 값 (실행 결과를 보고 고치지 않음)
# 기준 데이터: kimchi_v1 (10/08 수정본 · 라벨 지문 5c2b4fc2c3e6)
# v1 (라벨 검수 단계 문서 4,602) → v2 (kimchi_v1 4,601) 개정 이유: audit_expected.md 9장
# ----------------------------------------------------------------------
EXPECTED_DOC_VERSION = "v2"
EXPECTED = {
    "jpg_count": 900,
    "txt_count": 900,
    "pair_count": 900,
    "missing_label": 0,
    "missing_image": 0,
    "empty_label": 0,
    "class4_files": 0,
    "format_errors": 0,
    "bbox_total": 4601,   # v1: 4602
    "class_0": 924,      # v1: 868 (10/08 Class 2→0 수정)
    "class_1": 1897,
    "class_2": 711,      # v1: 767
    "class_3": 378,
    "class_4": 0,
    "class_5": 439,      # v1: 441
    "class_6": 252,      # v1: 251
    "manifest_rows": 900,
    "not_in_manifest": 0,
    "missing_in_dataset": 0,
}

ISSUE_FIELDS = ["file", "line", "issue_type", "severity", "detail"]


def main():
    parser = argparse.ArgumentParser(description="검수 완료 데이터셋 Dataset Audit")
    parser.add_argument("--fixture", action="store_true",
                        help="작은 테스트 데이터(data/audit_test)로 검사기 자체를 시험")
    args = parser.parse_args()

    if args.fixture:
        # 작은 테스트: Manifest·기대값 대조는 하지 않음 (5장뿐이라 의미 없음)
        data_dir, manifest, out_dir = FIXTURE_DIR, None, FIXTURE_DIR
    else:
        data_dir, manifest, out_dir = FINAL_DIR, MANIFEST, REPORT_DIR
        if not MANIFEST.exists():
            raise FileNotFoundError(f"Manifest를 찾을 수 없습니다: {MANIFEST}")

    # 1. 검사 실행
    issues, stats, image_rows = audit_dataset(
        data_dir / "images", data_dir / "labels", manifest
    )

    # 2. 화면 출력: 통계
    print(f"\n=== Audit 대상: {data_dir} ===")
    for key, value in stats.items():
        print(f"  {key:<22}: {value}")

    # 3. 화면 출력: 문제 종류별 개수
    print(f"\n=== 발견된 문제: {len(issues)}건 ===")
    counts: dict[str, int] = {}
    for i in issues:
        counts[i["issue_type"]] = counts.get(i["issue_type"], 0) + 1
    for issue_type, n in sorted(counts.items()):
        print(f"  {issue_type:<22}: {n}")

    # 4. 파일로 저장 (화면에만 두지 않고 나중에 다시 볼 수 있게)
    write_csv(issues, out_dir / "audit_issue.csv", ISSUE_FIELDS)
    print(f"\n저장: {out_dir / 'audit_issue.csv'}")

    if args.fixture:
        return

    # 5. 기대값 대조 (전체 실행일 때만)
    check_rows = compare_with_expected(stats, EXPECTED)
    write_csv(check_rows, REPORT_DIR / "audit_check.csv",
              ["item", "expected", "actual", "result"])

    stat_fields = (["file_name", "source_dataset", "original_split", "scene_type", "n_bbox"]
                   + [f"class_{c}" for c in VALID_CLASSES])
    write_csv(image_rows, REPORT_DIR / "audit_label_stats.csv", stat_fields)

    n_fail = sum(r["result"] == "FAIL" for r in check_rows)
    print(f"\n=== 기대값 대조: PASS {len(check_rows) - n_fail} / FAIL {n_fail} ===")
    for r in check_rows:
        if r["result"] == "FAIL":
            print(f"  FAIL {r['item']}: 기대 {r['expected']} / 실제 {r['actual']}")
    print(f"저장: {REPORT_DIR / 'audit_check.csv'}")
    print(f"저장: {REPORT_DIR / 'audit_label_stats.csv'}")


if __name__ == "__main__":
    main()
