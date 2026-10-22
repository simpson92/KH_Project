"""Split 배정 (Split 단계 선행)

    ① 5분 세션(G01~G18)을 배정 단위로 만든다
         - G18(object_only)  → Train 고정            (정책 6.1)
         - G01(파·고추)      → 2분 하위 세션으로 나눠 고정 배정 (정책 6.2 예외 E1)
    ② 나머지 김치 세션으로 Val / Frozen Test / Bridge 조합을 '전부' 검사한다 (전수 탐색)
    ③ 합격 기준을 통과한 조합 중 정책 8장 순서로 1개를 고른다
    ④ 고른 결과를 '파일 단위'로 다시 검증한다 (탐색 코드와 따로 계산 → 이중 확인)

사용법 (detection-model 폴더에서, 2·3단계 결과 CSV가 있어야 함):
    python scripts/05_make_split.py

결과 (파일명 · 숫자만, 이미지 없음):
    splits/kimchi_v1_split.csv      파일별 역할 (file_name, capture_group, role)
    reports/split_check.csv         합격 기준 8개 PASS / FAIL
    reports/split_summary.csv       역할별 이미지 · BBox · Class 수 · 날짜 · 세션
"""
from itertools import combinations
from pathlib import Path
import hashlib
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_ROOT / "reports"
SPLIT_DIR = PROJECT_ROOT / "splits"

# ----------------------------------------------------------------------
# 정책 값 (docs/split_policy.md 와 같아야 함 · 바꾸려면 문서부터 고친다)
# ----------------------------------------------------------------------
ROLES = ["train", "val", "test", "bridge"]
TARGET = {"train": 600, "val": 75, "test": 75, "bridge": 150}    # 5장
TOL = 10                                                          # ±10장
EVAL_CLASSES = [0, 1, 2, 3, 5, 6]                                 # Class 4 제외
MIN_EVAL = 20       # Frozen Test · Bridge  Class별 최소 (7장 4번)
MIN_TRAIN = 100     # Train                 Class별 최소 (7장 7번)
MIN_VAL = 1         # Val                   Class별 최소 (7장 8번)
MIN_DATES = 2       # Val · Test · Bridge   날짜 수 최소 (7장 5번)

OBJECT_ONLY_GROUP = "G18"    # 정책 6.1 → Train
E1_GROUP = "G01"             # 정책 6.2 예외 E1
E1_GAP_MIN = 2               # G01 안에서 2분 넘게 쉬면 하위 세션 경계
E1_ASSIGN = {1: "test", 2: "test", 3: "bridge", 4: "val", 5: "train"}   # S1~S5 배정

CLASS_COLS = [f"class_{c}" for c in EVAL_CLASSES]


# ----------------------------------------------------------------------
# ① 데이터 준비
# ----------------------------------------------------------------------
def load_images() -> pd.DataFrame:
    """이미지별 촬영 시각 · 5분 세션 · Class 수를 한 표로 합친다."""
    groups = pd.read_csv(REPORT_DIR / "capture_groups.csv", encoding="utf-8-sig",
                         parse_dates=["capture_time"])
    stats = pd.read_csv(REPORT_DIR / "audit_label_stats.csv", encoding="utf-8-sig")
    df = groups.merge(stats[["file_name"] + CLASS_COLS], on="file_name", how="left")
    if len(df) != 900 or df[CLASS_COLS].isna().any().any():
        raise ValueError("capture_groups.csv 와 audit_label_stats.csv 가 900장으로 맞지 않습니다.")
    df["group"] = df["group_5m"].map(lambda n: f"G{int(n):02d}")   # 1 → G01
    df["date"] = df["date"].astype(str)
    return df.sort_values("capture_time").reset_index(drop=True)


def split_e1(df: pd.DataFrame) -> pd.Series:
    """G01을 2분 하위 세션(S1~S5)으로 나눠 '이미지별 배정 단위 이름'을 돌려준다."""
    unit = df["group"].copy()
    g = df[df["group"] == E1_GROUP]
    gap = g["capture_time"].diff()
    sub_no = (gap.isna() | (gap > pd.Timedelta(minutes=E1_GAP_MIN))).cumsum()
    if sorted(sub_no.unique()) != sorted(E1_ASSIGN):
        # 정책 표(S1~S5)와 실제 데이터가 다르면 멈춘다 → 문서와 코드가 어긋난 것
        raise ValueError(f"{E1_GROUP} 하위 세션 수가 정책과 다릅니다: {sorted(sub_no.unique())}")
    unit.loc[g.index] = [f"{E1_GROUP}-S{n}" for n in sub_no]
    return unit


# ----------------------------------------------------------------------
# ② 전수 탐색
# ----------------------------------------------------------------------
def subsets_in_range(names, size, lo, hi):
    """names 중에서 이미지 수 합이 lo~hi 인 모든 조합 (작은 조합부터, 이름 순)."""
    out = []
    for r in range(1, len(names) + 1):
        for comb in combinations(names, r):
            s = sum(size[n] for n in comb)
            if lo <= s <= hi:
                out.append(comb)
    return out


def search(units: pd.DataFrame, fixed: dict) -> tuple[list, int]:
    """합격 기준을 통과하는 (val, test, bridge) 조합을 전부 찾고 정렬해서 돌려준다.

    units : 배정 단위(세션)별 images · date · Class 수 표 (index = 단위 이름)
    fixed : 이미 배정이 정해진 단위 {단위: 역할}
    """
    free = sorted(n for n in units.index if n not in fixed)
    size = units["images"].to_dict()
    cls = units[CLASS_COLS]
    dates = units["date"].to_dict()

    def role_stats(role, chosen):
        names = [n for n, r in fixed.items() if r == role] + list(chosen)
        return (sum(size[n] for n in names),
                cls.loc[names].sum(),
                {dates[n] for n in names})

    def fixed_size(role):
        return sum(size[n] for n, r in fixed.items() if r == role)

    def window(role):
        return TARGET[role] - TOL - fixed_size(role), TARGET[role] + TOL - fixed_size(role)

    found = []
    for test in subsets_in_range(free, size, *window("test")):
        n_t, c_t, d_t = role_stats("test", test)
        if c_t.min() < MIN_EVAL or len(d_t) < MIN_DATES:
            continue
        rest1 = [n for n in free if n not in test]
        for val in subsets_in_range(rest1, size, *window("val")):
            n_v, c_v, d_v = role_stats("val", val)
            if c_v.min() < MIN_VAL or len(d_v) < MIN_DATES:
                continue
            rest2 = [n for n in rest1 if n not in val]
            for bridge in subsets_in_range(rest2, size, *window("bridge")):
                n_b, c_b, d_b = role_stats("bridge", bridge)
                if c_b.min() < MIN_EVAL or len(d_b) < MIN_DATES:
                    continue
                train = [n for n in rest2 if n not in bridge]
                n_tr, c_tr, _ = role_stats("train", train)
                if c_tr.min() < MIN_TRAIN or abs(n_tr - TARGET["train"]) > TOL:
                    continue
                dev = sum(abs(n - TARGET[r]) for n, r in
                          [(n_tr, "train"), (n_v, "val"), (n_t, "test"), (n_b, "bridge")])
                eval_min = int(min(c_t.min(), c_b.min()))
                found.append({"dev": dev, "eval_min": eval_min,
                              "val": val, "test": test, "bridge": bridge, "train": tuple(train)})

    # 정책 8장 순서: ① 목표와 차이 작은 것 ② 평가 Class 최소 개수 큰 것 ③ 이름 순
    found.sort(key=lambda x: (x["dev"], -x["eval_min"], x["test"], x["val"], x["bridge"]))
    return found, len(found)


# ----------------------------------------------------------------------
# ④ 파일 단위 검증 (탐색 코드와 독립적으로 다시 계산)
# ----------------------------------------------------------------------
def verify(df: pd.DataFrame) -> list[dict]:
    rows = []

    def add(no, name, expected, actual, ok):
        rows.append({"no": no, "criterion": name, "expected": expected,
                     "actual": actual, "result": "PASS" if ok else "FAIL"})

    # 1. 누락 · 중복
    dup = df["file_name"].duplicated().sum()
    add(1, "누락 · 중복", "900장 · 중복 0 · 역할 없음 0",
        f"{len(df)}장 · 중복 {dup} · 역할 없음 {df['role'].isna().sum()}",
        len(df) == 900 and dup == 0 and df["role"].notna().all())

    # 2. Leakage: 5분 세션이 두 역할에 걸치는 경우 (E1 제외)
    span = df.groupby("group")["role"].nunique()
    leak = [g for g, n in span.items() if n > 1 and g != E1_GROUP]
    add(2, "Leakage (세션 걸침, E1 제외)", "0건", f"{len(leak)}건 {leak if leak else ''}", not leak)

    # 3. 수량
    cnt = df["role"].value_counts()
    ok3 = all(abs(cnt.get(r, 0) - TARGET[r]) <= TOL for r in ROLES)
    add(3, "수량 (±10장)", " / ".join(f"{r} {TARGET[r]}" for r in ROLES),
        " / ".join(f"{r} {cnt.get(r, 0)}" for r in ROLES), ok3)

    by_role = df.groupby("role")[CLASS_COLS].sum()

    # 4. Frozen Test · Bridge Class 최소
    m4 = int(by_role.loc[["test", "bridge"]].min().min())
    add(4, "Test · Bridge Class별 최소", f">= {MIN_EVAL}", m4, m4 >= MIN_EVAL)

    # 5. 장면 · 날짜
    ev = df[df["role"].isin(["val", "test", "bridge"])]
    only_kimchi = (ev["scene_type"] == "kimchi_with_target").all()
    n_dates = ev.groupby("role")["date"].nunique()
    add(5, "Val · Test · Bridge 김치 장면만 · 날짜 2개 이상", f"김치만 · >= {MIN_DATES}",
        f"김치만 {only_kimchi} · " + " / ".join(f"{r} {n_dates[r]}" for r in ["val", "test", "bridge"]),
        only_kimchi and (n_dates >= MIN_DATES).all())

    # 6. 재현성: main()에서 탐색을 두 번 돌려 비교한 결과를 넣음 (아래 참고)

    # 7. Train Class 최소
    m7 = int(by_role.loc["train"].min())
    add(7, "Train Class별 최소", f">= {MIN_TRAIN}", m7, m7 >= MIN_TRAIN)

    # 8. Val Class 최소
    m8 = int(by_role.loc["val"].min())
    add(8, "Val Class별 최소", f">= {MIN_VAL}", m8, m8 >= MIN_VAL)

    return rows


def fingerprint(names) -> str:
    """파일명 목록의 sha256 앞 12자리 (정렬 후 계산 → 순서와 무관)."""
    text = "\n".join(sorted(names)).encode("utf-8")
    return hashlib.sha256(text).hexdigest()[:12]


def main():
    df = load_images()
    df["unit"] = split_e1(df)

    # 배정 단위(세션 · E1 하위 세션)별 요약
    units = df.groupby("unit").agg(images=("file_name", "count"), date=("date", "first"),
                                   **{c: (c, "sum") for c in CLASS_COLS})

    # 고정 배정: G18 → Train, G01 하위 세션 → E1 표
    fixed = {OBJECT_ONLY_GROUP: "train"}
    fixed.update({f"{E1_GROUP}-S{n}": r for n, r in E1_ASSIGN.items()})

    # ②③ 전수 탐색 (재현성 확인을 위해 두 번 실행)
    found, n_found = search(units, fixed)
    found2, _ = search(units, fixed)
    if not found:
        sys.exit("합격 기준을 모두 만족하는 조합이 없습니다 → split_policy.md 기준을 다시 논의하세요.")
    best = found[0]
    reproducible = best == found2[0]

    assign = dict(fixed)
    for role in ["val", "test", "bridge", "train"]:
        assign.update({u: role for u in best[role]})
    df["role"] = df["unit"].map(assign)

    # ④ 파일 단위 검증
    checks = verify(df)
    checks.insert(5, {"no": 6, "criterion": "재현성 (두 번 실행 결과 동일)", "expected": "동일",
                      "actual": "동일" if reproducible else "다름",
                      "result": "PASS" if reproducible else "FAIL"})

    # 저장
    SPLIT_DIR.mkdir(exist_ok=True)
    out = df.sort_values("file_name")[["file_name", "unit", "role"]].rename(columns={"unit": "capture_group"})
    out.to_csv(SPLIT_DIR / "kimchi_v1_split.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(checks).to_csv(REPORT_DIR / "split_check.csv", index=False, encoding="utf-8-sig")

    summary = df.groupby("role").agg(images=("file_name", "count"), bbox=("n_bbox", "sum"),
                                     **{c: (c, "sum") for c in CLASS_COLS},
                                     dates=("date", lambda s: " ".join(sorted(s.unique()))),
                                     groups=("unit", lambda s: " ".join(sorted(s.unique()))))
    summary = summary.reindex(ROLES).reset_index()
    summary.to_csv(REPORT_DIR / "split_summary.csv", index=False, encoding="utf-8-sig")

    # 화면 출력
    pd.set_option("display.width", 220)
    print(f"\n=== 전수 탐색: 합격 기준을 만족하는 조합 {n_found:,}개 중 1순위 선택 ===")
    print(f"  목표와 차이 합계 {best['dev']}장 · Test·Bridge Class 최소 {best['eval_min']}개")
    print("\n=== 역할별 요약 ===")
    print(summary.to_string(index=False))
    print("\n=== 합격 기준 ===")
    for c in checks:
        print(f"  {c['result']}  {c['no']}. {c['criterion']:<36} 기대 {c['expected']} / 실제 {c['actual']}")
    n_fail = sum(c["result"] == "FAIL" for c in checks)
    print(f"\n  → PASS {len(checks) - n_fail} / FAIL {n_fail}")

    test_fp = fingerprint(df.loc[df["role"] == "test", "file_name"])
    print(f"\nFrozen Test 지문 (파일명 sha256 앞 12자리): {test_fp}  ← split_policy.md 8장에 기록")
    print(f"저장: splits/kimchi_v1_split.csv · reports/split_check.csv · reports/split_summary.csv")


if __name__ == "__main__":
    main()