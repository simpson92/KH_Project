"""데이터 감사 단계 (3번째 검사): Split 정책을 정하기 전 '데이터 지도' 그리기.

    ① Class × scene_type 분포       → 어떤 Class가 어디에 몰려 있나
    ② 촬영 시각 확인 (파일명 vs EXIF) → 파일명이 정말 촬영 시각인가
    ③ capture_group 기준 비교 (1·5·10분) → 세션을 몇 분 간격으로 끊을까
    ④ Leakage 재확인 (기존 validation ↔ train 60초 이내)

사용법 (detection-model 폴더에서 실행, 2단계 Audit을 먼저 실행해야 함):
    python scripts/04_split_analysis.py            # 상세 표는 5분 기준
    python scripts/04_split_analysis.py --gap 10   # 상세 표를 10분 기준으로

결과 (전부 파일명 · 숫자만 있음, 이미지 없음):
    reports/class_scene_distribution.csv   ① 출처 · split · scene_type별 이미지 수와 Class별 BBox
    reports/filename_time_check.csv        ② 파일명 시각 vs EXIF 시각
    reports/capture_group_compare.csv      ③ 기준(분)별 세션 수 · 섞임 정도
    reports/capture_groups.csv             ③ 이미지별 촬영 시각 + 기준별 그룹 번호 (4단계 Split 입력)
    reports/capture_group_summary.csv      ③ --gap 기준 세션별 상세
"""
from pathlib import Path
import argparse
import sys

import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.capture_group import parse_capture_time, assign_capture_groups, nearest_gap_seconds

STATS_CSV = PROJECT_ROOT / "reports" / "audit_label_stats.csv"   # 2단계 결과
IMAGES_DIR = PROJECT_ROOT / "data" / "subject7_final" / "images"
REPORT_DIR = PROJECT_ROOT / "reports"

GAP_CANDIDATES = [1, 5, 10]          # 비교할 세션 경계 기준 (분)
LEAK_SECONDS = 60                     # "유사 장면"으로 볼 시간 차
CLASS_COLS = [f"class_{c}" for c in range(7)]

# 기대값: reports/audit_expected.md 5장 (실행 결과를 보고 고치지 않음)
EXPECTED_LEAK = {"val_within_60s": 136, "val_total": 180, "min_gap_sec": 8,
                 "groups_5m": 18, "mixed_groups_5m": 17}


def save(df: pd.DataFrame, name: str) -> None:
    """reports/에 CSV 저장 (엑셀 한글 깨짐 방지 utf-8-sig)."""
    df.to_csv(REPORT_DIR / name, index=False, encoding="utf-8-sig")
    print(f"  저장: reports/{name}")


# ----------------------------------------------------------------------
# ① Class × scene_type 분포
# ----------------------------------------------------------------------
def class_scene_distribution(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["source_dataset", "original_split", "scene_type"]
    table = df.groupby(keys).agg(images=("file_name", "count"),
                                 bbox=("n_bbox", "sum"),
                                 **{c: (c, "sum") for c in CLASS_COLS}).reset_index()
    # 맨 아래에 합계 줄 추가
    total = table[["images", "bbox"] + CLASS_COLS].sum()
    total_row = {"source_dataset": "합계", "original_split": "", "scene_type": "", **total}
    return pd.concat([table, pd.DataFrame([total_row])], ignore_index=True)


# ----------------------------------------------------------------------
# ② 파일명 시각 vs EXIF 시각
# ----------------------------------------------------------------------
def read_exif_time(path: Path):
    """사진의 EXIF 촬영 시각을 읽는다. 없으면 None."""
    try:
        exif = Image.open(path).getexif()
    except OSError:
        return None
    # 36867 = DateTimeOriginal(촬영 시각, Exif 영역) / 306 = DateTime(기본 영역)
    raw = exif.get_ifd(0x8769).get(36867) or exif.get(306)
    if not raw:
        return None
    try:
        return pd.to_datetime(raw, format="%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def filename_time_check(df: pd.DataFrame) -> pd.DataFrame:
    """날짜별 첫 장 · 가운데 · 마지막 장을 골라 파일명 시각과 EXIF 시각을 비교."""
    rows = []
    for _, day in df.sort_values("capture_time").groupby("date"):
        for i in sorted({0, len(day) // 2, len(day) - 1}):
            r = day.iloc[i]
            exif_time = read_exif_time(IMAGES_DIR / r["file_name"])
            diff = (abs((exif_time - r["capture_time"]).total_seconds())
                    if exif_time is not None else None)
            rows.append({"file_name": r["file_name"],
                         "filename_time": r["capture_time"].strftime("%Y-%m-%d %H:%M:%S"),
                         "exif_time": exif_time.strftime("%Y-%m-%d %H:%M:%S") if exif_time is not None else "EXIF 없음",
                         "diff_sec": diff})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# ③ capture_group 기준 비교
# ----------------------------------------------------------------------
def compare_gaps(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for gap in GAP_CANDIDATES:
        g = df.groupby(f"group_{gap}m")
        n_split = g["original_split"].nunique()       # 한 그룹 안의 split 종류 수
        n_scene = g["scene_type"].nunique()
        size = g.size()
        # train과 validation이 섞인 그룹에 들어 있는 validation 이미지 수
        mixed_ids = n_split[n_split > 1].index
        val_in_mixed = df[df[f"group_{gap}m"].isin(mixed_ids)
                          & (df["original_split"] == "validation")].shape[0]
        rows.append({"gap_min": gap,
                     "groups": len(size),
                     "max_images": int(size.max()),
                     "min_images": int(size.min()),
                     "single_image_groups": int((size == 1).sum()),
                     "mixed_split_groups": int((n_split > 1).sum()),
                     "mixed_scene_groups": int((n_scene > 1).sum()),
                     "val_in_mixed_groups": val_in_mixed})
    return pd.DataFrame(rows)


def group_summary(df: pd.DataFrame, gap: int) -> pd.DataFrame:
    col = f"group_{gap}m"
    rows = []
    for gid, g in df.sort_values("capture_time").groupby(col):
        rows.append({
            "group": f"G{gid:02d}",
            "date": g["date"].iloc[0],
            "start": g["capture_time"].min().strftime("%H:%M:%S"),
            "end": g["capture_time"].max().strftime("%H:%M:%S"),
            "minutes": round((g["capture_time"].max() - g["capture_time"].min()).total_seconds() / 60, 1),
            "images": len(g),
            "train": int((g["original_split"] == "train").sum()),
            "validation": int((g["original_split"] == "validation").sum()),
            "kimchi_with_target": int((g["scene_type"] == "kimchi_with_target").sum()),
            "object_only": int((g["scene_type"] == "object_only").sum()),
            "bbox": int(g["n_bbox"].sum()),
            **{c: int(g[c].sum()) for c in CLASS_COLS},
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="데이터 감사 단계 분포 · Leakage 분석")
    parser.add_argument("--gap", type=int, default=5, choices=GAP_CANDIDATES,
                        help="세션별 상세 표를 만들 기준 (분)")
    args = parser.parse_args()

    if not STATS_CSV.exists():
        raise FileNotFoundError(f"2단계 Audit 결과가 없습니다: {STATS_CSV}")
    df = pd.read_csv(STATS_CSV, encoding="utf-8-sig")
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)

    # 파일명 → 촬영 시각 · 날짜 컬럼 추가
    df["capture_time"] = df["file_name"].map(parse_capture_time)
    df["date"] = df["file_name"].str[:6]

    print("\n=== ① 출처 · split · scene_type별 이미지 수와 Class별 BBox ===")
    dist = class_scene_distribution(df)
    print(dist.to_string(index=False))
    save(dist, "class_scene_distribution.csv")

    print("\n=== ② 파일명 시각 vs EXIF 시각 (날짜별 3장) ===")
    check = filename_time_check(df)
    print(check.to_string(index=False))
    save(check, "filename_time_check.csv")

    print("\n=== ③ capture_group 기준 비교 ===")
    for gap in GAP_CANDIDATES:
        df[f"group_{gap}m"] = assign_capture_groups(df["capture_time"], gap)
    cmp_table = compare_gaps(df)
    print(cmp_table.to_string(index=False))
    save(cmp_table, "capture_group_compare.csv")

    out_cols = (["file_name", "capture_time", "date", "source_dataset", "original_split",
                 "scene_type", "n_bbox"] + [f"group_{g}m" for g in GAP_CANDIDATES])
    save(df[out_cols], "capture_groups.csv")

    print(f"\n=== ③ 세션별 상세 ({args.gap}분 기준) ===")
    summary = group_summary(df, args.gap)
    print(summary.drop(columns=CLASS_COLS).to_string(index=False))
    save(summary, "capture_group_summary.csv")

    print(f"\n=== ④ Leakage 재확인 (기존 validation ↔ 가장 가까운 train) ===")
    val = df[df["original_split"] == "validation"]
    train = df[df["original_split"] == "train"]
    gaps = nearest_gap_seconds(val["capture_time"], train["capture_time"])
    actual = {"val_within_60s": int((gaps <= LEAK_SECONDS).sum()),
              "val_total": len(val),
              "min_gap_sec": int(gaps.min()),
              "groups_5m": int(cmp_table.loc[cmp_table.gap_min == 5, "groups"].iloc[0]),
              "mixed_groups_5m": int(cmp_table.loc[cmp_table.gap_min == 5, "mixed_split_groups"].iloc[0])}
    for k, exp in EXPECTED_LEAK.items():
        print(f"  {'PASS' if actual[k] == exp else 'FAIL'}  {k:<16} 기대 {exp:>4} / 실제 {actual[k]:>4}")


if __name__ == "__main__":
    main()
