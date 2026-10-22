"""실패 분석 단계 준비: Val 의 branch(Class 2) 예측을 하나씩 분류한다 (가설 H3 · branch 오검출 확인).

사용법 (detection-model 폴더에서 · venv 켠 뒤):
    python scripts/12_branch_fp_check.py              # 기본 conf 0.25 (11 과 같은 기준)

입력:
    models/baseline/baseline_best.pt        Baseline (sha 가 baseline_training_condition.md 와 같아야 함)
    data/yolo/{images,labels}/val           08 이 만들고 09 가 검증한 Val (74장)
    manifests/val.csv                       scene_type · capture_group
    reports/baseline_val_image_check.csv    Baseline 평가 단계 11 결과 (용훈 PC) → "내 PC 예측 = 용훈 PC 예측" 비교용

결과:
    reports/branch_pred_check.csv           branch 예측 1개 = 1행 (파일명 · 좌표 · 분류 · 사람 확인 칸)   (Git · 이미지 없음)
    runs/predict/branch_check/              박스 그린 Val 이미지 (Git 제외 · NDA · 사람 확인용 · 외부 공유 금지)

branch 예측 분류 (IoU 기준 0.5 · 09 · match_boxes 와 같은 짝짓기):
    TP              branch 정답과 IoU ≥ 0.5 로 짝지어짐
    중복            이미 다른 branch 예측이 잡은 branch 정답 위에 또 그린 박스
    다른 이물 위    다른 Class 정답과 IoU ≥ 0.5  → Class 혼동 (예: plastic 을 branch 로)
    위치 어긋남     어떤 정답과 0.1 ≤ IoU < 0.5  → 근처 이물을 대충 잡음
    정답 없는 자리  모든 정답과 IoU < 0.1        → 사람이 확인: 라벨 누락 / 김치 줄기 착각 / 기타

원칙:
    - Val 만 쓴다 (Frozen Test · Bridge Holdout 사용 안 함).
    - src/ 코드는 고치지 않고 가져다 쓴다 (Baseline 평가 단계 리뷰가 끝난 코드).
    - data/yolo 는 읽기만 한다.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import re
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]          # scripts/ 한 단계 위 = detection-model/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from src.manifest import read_manifest
from src.evaluate_detector import predict_images, match_boxes, iou_xywh

# ----------------------------------------------------------------------
# 경로 · 기준값
# ----------------------------------------------------------------------
BEST_PT = PROJECT_ROOT / "models" / "baseline" / "baseline_best.pt"
CONDITION_MD = PROJECT_ROOT / "reports" / "baseline_training_condition.md"
DATASET_YAML = PROJECT_ROOT / "configs" / "dataset.yaml"
VAL_CSV = PROJECT_ROOT / "manifests" / "val.csv"
VAL_IMAGES = PROJECT_ROOT / "data" / "yolo" / "images" / "val"
VAL_LABELS = PROJECT_ROOT / "data" / "yolo" / "labels" / "val"
VERIFY_SCRIPT = PROJECT_ROOT / "scripts" / "09_verify_yolo_dataset.py"
IMAGE_CHECK_CSV = PROJECT_ROOT / "reports" / "baseline_val_image_check.csv"   # Baseline 평가 단계 용훈 PC 결과 (읽기만)
OUT_CSV = PROJECT_ROOT / "reports" / "branch_pred_check.csv"
RUNS_DIR = PROJECT_ROOT / "runs"
PRED_RUN_NAME = "branch_check"

BRANCH = 2                 # configs/dataset.yaml → 2: branch
IOU_MATCH = 0.5            # 11 과 같은 짝 기준
IOU_NEAR = 0.1             # 이보다 작으면 "정답 없는 자리"
IMGSZ = 640
N_VAL = 74
ULTRALYTICS_VERSION = "8.4.175"


def sha12(path: Path) -> str:
    """파일 지문 앞 12자리 (가중치가 용훈 PC 와 같은 파일인지 확인)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def recorded_sha() -> str:
    """Baseline 학습 단계 조건 문서에 적힌 baseline_best.pt sha."""
    text = CONDITION_MD.read_text(encoding="utf-8") if CONDITION_MD.exists() else ""
    m = re.search(r"baseline_best\.pt` · sha `([0-9a-f]{12})`", text)
    return m.group(1) if m else "-"


def pre_checks() -> list[dict]:
    """실행 전 검사 6개 — 하나라도 FAIL 이면 예측하지 않는다."""
    checks = []

    def add(item, expected, actual, ok=None):
        ok = (str(expected) == str(actual)) if ok is None else ok
        checks.append({"item": item, "expected": expected, "actual": actual, "result": "PASS" if ok else "FAIL"})

    try:
        import ultralytics
        ver = ultralytics.__version__
    except ImportError:
        ver = "없음 (venv 를 켰나요?)"
    add("Ultralytics 버전 (팀 고정)", ULTRALYTICS_VERSION, ver)
    add("Baseline Weight 위치", "models/baseline/baseline_best.pt", "있음" if BEST_PT.exists() else "없음",
        ok=BEST_PT.exists())
    add("Weight sha = Baseline 학습 단계 기록", recorded_sha(), sha12(BEST_PT) if BEST_PT.exists() else "-")

    data_yaml = yaml.safe_load(DATASET_YAML.read_text(encoding="utf-8"))
    add("dataset.yaml 2번 = branch", "branch", data_yaml.get("names", {}).get(BRANCH, "-"))

    n_img = len(list(VAL_IMAGES.glob("*.jpg"))) if VAL_IMAGES.exists() else 0
    add("Val 이미지 수", N_VAL, n_img)

    r = subprocess.run([sys.executable, str(VERIFY_SCRIPT)], cwd=PROJECT_ROOT, capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or ["(출력 없음)"])[-1].strip()
    add("09 data/yolo 검증", "종료 코드 0", f"종료 코드 {r.returncode} · {last}", ok=(r.returncode == 0))
    return checks


def read_gt(stem: str) -> list[tuple]:
    """정답 라벨 TXT → [(cls, x, y, w, h), ...]  (0~1 좌표)"""
    out = []
    for line in (VAL_LABELS / f"{stem}.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 5:
            out.append((int(parts[0]), *map(float, parts[1:])))
    return out


def match_detail(gts, preds, iou_thr=IOU_MATCH) -> list:
    """match_boxes 와 같은 규칙(점수 높은 예측부터 · 같은 Class · 한 GT 는 한 번만)으로
    예측마다 '짝지어진 GT 번호'(없으면 None)를 돌려준다. match_boxes 는 개수만 주기 때문에 따로 둔다."""
    used, matched = set(), [None] * len(preds)
    for j in sorted(range(len(preds)), key=lambda j: -preds[j][1]):
        p, best_i, best_iou = preds[j], None, iou_thr
        for i, g in enumerate(gts):
            if i in used or g[0] != p[0]:
                continue
            v = iou_xywh(g[1:], p[2:])
            if v >= best_iou:
                best_i, best_iou = i, v
        if best_i is not None:
            used.add(best_i)
            matched[j] = best_i
    return matched


def classify(j, preds, gts, matched) -> tuple[str, float, str, str]:
    """branch 예측 하나 → (분류, 가장 많이 겹친 정답과의 IoU, 그 정답 Class, 그 정답을 다른 예측이 맞혔는지)"""
    if matched[j] is not None:
        return "TP", 1.0, "branch", "-"
    p = preds[j]
    if not gts:
        return "정답 없는 자리", 0.0, "-", "-"
    ious = [iou_xywh(g[1:], p[2:]) for g in gts]
    i = max(range(len(gts)), key=lambda k: ious[k])
    g_cls = gts[i][0]
    found = "yes" if i in matched else "no"           # 그 정답을 (올바른 Class 로) 다른 예측이 이미 맞혔는가
    if ious[i] >= IOU_MATCH:
        kind = "중복" if g_cls == BRANCH else "다른 이물 위"
    elif ious[i] >= IOU_NEAR:
        kind = "위치 어긋남"
    else:
        return "정답 없는 자리", ious[i], "-", "-"      # 겹친 정답이 사실상 없음 → 정답 Class 칸은 비움
    return kind, ious[i], g_cls, found


def main():
    parser = argparse.ArgumentParser(description="Val branch 예측 분류 (H3 · branch 오검출 확인)")
    parser.add_argument("--conf", type=float, default=0.25, help="예측 conf (기본 0.25 · 09 와 같음)")
    args = parser.parse_args()

    checks = pre_checks()
    print("=== 실행 전 검사 ===")
    for c in checks:
        print(f"  {c['result']}  {c['item']:<26} 기대 {c['expected']} / 실제 {c['actual']}")
    n_fail = sum(c["result"] == "FAIL" for c in checks)
    print(f"  → PASS {len(checks) - n_fail} / FAIL {n_fail}")
    if n_fail:
        sys.exit("\n[중단] FAIL 이 있어 예측하지 않았습니다. (안내서 '막혔을 때' 표를 보세요)")

    names = {int(k): v for k, v in yaml.safe_load(DATASET_YAML.read_text(encoding="utf-8"))["names"].items()}
    val_info = {r["file_name"]: r for r in read_manifest(VAL_CSV)[0]}
    ref = {}
    if IMAGE_CHECK_CSV.exists():
        with open(IMAGE_CHECK_CSV, encoding="utf-8-sig") as f:
            ref = {r["file_name"]: r for r in csv.DictReader(f)}

    print(f"\n=== Val 예측 (conf {args.conf} · imgsz {IMGSZ}) ===")
    rows, diff, n_img = [], [], 0
    branch_gt = {"gt": 0, "found": 0}
    for name, (w_img, h_img), preds in predict_images(str(BEST_PT), VAL_IMAGES, args.conf, IMGSZ,
                                                      RUNS_DIR / "predict", PRED_RUN_NAME):
        n_img += 1
        gts = read_gt(Path(name).stem)
        m = match_boxes(gts, preds, IOU_MATCH)
        matched = match_detail(gts, preds, IOU_MATCH)
        assert sum(x is not None for x in matched) == m["tp"], "짝짓기 결과가 match_boxes 와 다릅니다"

        # ① 용훈 PC(Baseline 평가 단계 11) 결과와 같은지: 이미지별 예측 · TP · FP · FN 개수 비교
        r0 = ref.get(name)
        mine = (len(preds), m["tp"], m["fp"], m["fn"])
        if r0 is None or mine != (int(r0["pred"]), int(r0["tp"]), int(r0["fp"]), int(r0["fn"])):
            diff.append((name, mine, None if r0 is None else (r0["pred"], r0["tp"], r0["fp"], r0["fn"])))

        # ② branch 정답을 찾았는지
        for i, g in enumerate(gts):
            if g[0] == BRANCH:
                branch_gt["gt"] += 1
                branch_gt["found"] += i in matched

        # ③ branch 예측 하나씩 분류
        info = val_info.get(name, {})
        scale = IMGSZ / max(w_img, h_img)
        for j, p in enumerate(preds):
            if p[0] != BRANCH:
                continue
            kind, iou, g_cls, found = classify(j, preds, gts, matched)
            _, conf, x, y, w, h = p
            rows.append({
                "file_name": name, "source_dataset": info.get("source_dataset", "-"),
                "scene_type": info.get("scene_type", "-"),
                "capture_group": info.get("capture_group", "-"),
                "conf": f"{conf:.3f}", "kind": kind, "best_iou": f"{iou:.2f}",
                "overlap_gt_class": names.get(g_cls, g_cls) if isinstance(g_cls, int) else g_cls,
                "gt_found_by_other": found,
                # 라벨링 프로그램에서 찾아갈 위치 (원본 사진 픽셀 · 왼쪽 위 / 오른쪽 아래)
                "x1": round((x - w / 2) * w_img), "y1": round((y - h / 2) * h_img),
                "x2": round((x + w / 2) * w_img), "y2": round((y + h / 2) * h_img),
                "size_640": f"{w * w_img * scale:.0f}x{h * h_img * scale:.0f}",
                "human_check": "",      # ← 김하민 님이 채움: 라벨 누락 / 김치 줄기 착각 / 다른 이물 / 판단 어려움
                "memo": "",             # ← 본 것 한 줄 (예: 배추 줄기 끝 갈색 부분)
            })

    order = {"정답 없는 자리": 0, "위치 어긋남": 1, "다른 이물 위": 2, "중복": 3, "TP": 4}
    rows.sort(key=lambda r: (order[r["kind"]], -float(r["conf"])))
    for k, r in enumerate(rows, 1):
        r["no"] = k
    fields = ["no", "file_name", "source_dataset", "scene_type", "capture_group", "conf", "kind", "best_iou", "overlap_gt_class",
              "gt_found_by_other", "x1", "y1", "x2", "y2", "size_640", "human_check", "memo"]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        wr.writeheader()
        wr.writerows(rows)

    # ── 출력 (이 텍스트만 팀에 공유 · 이미지는 공유 금지) ─────────────────────────
    print(f"\n=== ① 용훈 PC 결과(reports/baseline_val_image_check.csv)와 비교 ===")
    print(f"  {n_img}장 중 같음 {n_img - len(diff)} · 다름 {len(diff)}")
    for name, mine, theirs in diff[:10]:
        print(f"    다름 {name}  내 PC (예측·TP·FP·FN) {mine} / 기록 {theirs}")

    print(f"\n=== ② branch 정답(GT) ===")
    print(f"  GT {branch_gt['gt']}개 · 찾음 {branch_gt['found']} · 놓침 {branch_gt['gt'] - branch_gt['found']}")

    print(f"\n=== ③ branch 예측 {len(rows)}개 분류 (conf {args.conf}) ===")
    for kind in order:
        sub = [r for r in rows if r["kind"] == kind]
        extra = ""
        if kind == "다른 이물 위" and sub:
            cnt = {}
            for r in sub:
                cnt[r["overlap_gt_class"]] = cnt.get(r["overlap_gt_class"], 0) + 1
            extra = "  ← 실제 정답: " + " · ".join(f"{c} {n}" for c, n in cnt.items())
        if kind == "정답 없는 자리" and sub:
            extra = "  ← 사람 확인 필요 (아래 목록)"
        print(f"  {kind:<10} {len(sub):>3}{extra}")

    todo = [r for r in rows if r["kind"] in ("정답 없는 자리", "위치 어긋남")]
    if todo:
        print(f"\n=== ④ 사람이 확인할 목록 ({len(todo)}개 · conf 높은 순) ===")
        print(f"  {'no':>3}  {'file_name':<26}{'conf':>6}  {'분류':<9}{'원본 좌표 (x1,y1)-(x2,y2)':<28}{'640 크기':>9}")
        for r in todo:
            box = f"({r['x1']},{r['y1']})-({r['x2']},{r['y2']})"
            print(f"  {r['no']:>3}  {r['file_name']:<26}{r['conf']:>6}  {r['kind']:<9}{box:<28}{r['size_640']:>9}")

    print("\n=== 저장 ===")
    print(f"  OK  {OUT_CSV.relative_to(PROJECT_ROOT)}   ← human_check · memo 칸을 채워서 커밋")
    print(f"  (Git 제외) runs/predict/{PRED_RUN_NAME}/   ← 박스 그린 Val 이미지 · 눈으로 확인만 · 외부 공유 금지")


if __name__ == "__main__":
    main()
