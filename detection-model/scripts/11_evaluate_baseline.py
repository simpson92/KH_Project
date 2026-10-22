"""Baseline 평가 단계: Baseline Validation 평가 · 이미지 Detection (산출물 2 완료 · 산출물 5 시작).

사용법 (detection-model 폴더에서 · Baseline 학습 단계 10 학습이 "완료" 된 뒤):
    python scripts/11_evaluate_baseline.py              # 검사 → Val 평가 → 그림 정리 → Val 예측 · 이미지별 FP/FN
    python scripts/11_evaluate_baseline.py --conf 0.25  # 예측 conf (기본 0.25 · 평가 지표는 conf 와 무관)

※ 요구사항 문서의 이름은 scripts/07_evaluate_baseline.py (+ 08_predict_images.py) 이지만,
  평가와 이미지 예측을 11 하나로 묶었다. 번호는 실행 순서대로 매겼다 (README 6.2 실행표).

입력:
    models/baseline/baseline_best.pt            Baseline (sha 는 baseline_training_condition.md 와 같아야 함)
    configs/dataset.yaml · configs/baseline.yaml  평가 데이터 · imgsz · batch (학습과 같은 값)
    manifests/val.csv · data/yolo/{images,labels}/val

결과:
    reports/baseline_metrics.csv                  산출물 2 · Val 전체 + Class별 P · R · mAP50 · mAP50-95   (Git)
    reports/figures/baseline_results.png          산출물 5 · 학습곡선 (runs/baseline_v1/results.png 사본)   (Git · 그래프)
    reports/figures/baseline_confusion_matrix.png 산출물 5 · Val Confusion Matrix (+ _normalized)        (Git · 그래프)
    reports/baseline_val_image_check.csv          진행용 · 이미지별 GT · 예측 · TP · FP · FN · 작은 객체 FN  (Git · 실패 분석 단계 입력)
    reports/baseline_class_check.csv              진행용 · Class별 GT · TP · FN · FP · 현장 기준(conf) Recall · Precision (Git · 개선 실험 단계 비교 기준)
    runs/baseline_v1_val/                         Ultralytics 평가 결과 (Git 제외)
    runs/predict/baseline_val_images/             박스 그린 Val 이미지 (Git 제외 · NDA · 실패 분석 단계 작업자료)

원칙:
    - Val 만 평가한다. Frozen Test · Bridge Holdout 은 쓰지 않는다 (evaluate_detector 가 test 를 거부).
    - reports/figures/ 에는 그래프만 둔다. 회사 이미지가 들어간 그림(val_batch*.jpg · 예측 이미지)은 runs/ 에만 남는다.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import re
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from src.manifest import read_manifest
from src.evaluate_detector import evaluate_detector, predict_images, match_boxes

# ----------------------------------------------------------------------
# 경로
# ----------------------------------------------------------------------
BEST_PT = PROJECT_ROOT / "models" / "baseline" / "baseline_best.pt"
CONDITION_MD = PROJECT_ROOT / "reports" / "baseline_training_condition.md"
BASELINE_YAML = PROJECT_ROOT / "configs" / "baseline.yaml"
DATASET_YAML = PROJECT_ROOT / "configs" / "dataset.yaml"
MANIFEST_DIR = PROJECT_ROOT / "manifests"
VAL_IMAGES = PROJECT_ROOT / "data" / "yolo" / "images" / "val"
VAL_LABELS = PROJECT_ROOT / "data" / "yolo" / "labels" / "val"
VERIFY_SCRIPT = PROJECT_ROOT / "scripts" / "09_verify_yolo_dataset.py"
RUNS_DIR = PROJECT_ROOT / "runs"
FIG_DIR = PROJECT_ROOT / "reports" / "figures"
METRICS_CSV = PROJECT_ROOT / "reports" / "baseline_metrics.csv"
IMAGE_CHECK_CSV = PROJECT_ROOT / "reports" / "baseline_val_image_check.csv"
CLASS_CHECK_CSV = PROJECT_ROOT / "reports" / "baseline_class_check.csv"

SPLIT = "val"                     # 이 스크립트는 val 만 평가한다
VAL_RUN_NAME = "baseline_v1_val"
PRED_RUN_NAME = "baseline_val_images"
IOU_MATCH = 0.5                   # 예측 ↔ GT 짝 기준 (mAP50 과 같은 IoU)
SMALL_PX = 32                     # 모델 입력(긴 변 640) 기준 32×32px 미만 = 작은 객체 (COCO small 기준)
UNUSED_CLASSES = {4: "미사용 Class (라벨 검수 단계 enabled: false)"}


def sha12(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def condition_info() -> dict:
    """Baseline 학습 단계 조건 문서에서 상태 · 가중치 sha · 학습 결과 폴더를 읽는다."""
    text = CONDITION_MD.read_text(encoding="utf-8") if CONDITION_MD.exists() else ""
    state = re.search(r"\*\*상태\*\*: ([^·\n]+)", text)
    sha = re.search(r"baseline_best\.pt` · sha `([0-9a-f]{12})`", text)
    return {"state": state.group(1).strip() if state else "문서 없음", "sha": sha.group(1) if sha else "-"}


def pre_checks(cfg: dict, train_name: str) -> list[dict]:
    checks = []

    def add(item, expected, actual, ok=None):
        ok = (str(expected) == str(actual)) if ok is None else ok
        checks.append({"item": item, "expected": expected, "actual": actual, "result": "PASS" if ok else "FAIL"})

    try:
        import ultralytics
        ver = ultralytics.__version__
    except ImportError:
        ver = "없음"
    add("Ultralytics 버전 (팀 고정)", str(cfg.get("ultralytics_version", "8.4.175")), ver)

    info = condition_info()
    add("학습 상태 (condition md)", "완료", info["state"])
    add("Baseline Weight 있음", "있음", "있음" if BEST_PT.exists() else "없음")
    add("Weight sha = Baseline 학습 단계 기록", info["sha"], sha12(BEST_PT) if BEST_PT.exists() else "-")
    add("학습곡선 원본 있음", f"runs/{train_name}/results.png",
        f"runs/{train_name}/results.png" if (RUNS_DIR / train_name / "results.png").exists() else "없음")

    data_yaml = yaml.safe_load(DATASET_YAML.read_text(encoding="utf-8"))
    yaml_text = " ".join(str(data_yaml.get(k, "")) for k in ("train", "val", "test"))
    add("dataset.yaml 에 Bridge 없음", "no", "yes" if "bridge" in yaml_text else "no")
    add("평가 split", "val", SPLIT)

    manifest, schema = read_manifest(MANIFEST_DIR / "split_manifest.csv")
    add("manifest 스키마", "v2", schema)
    add("Dataset Version", cfg.get("dataset_version", "kimchi_v1"),
        ",".join(sorted({r.get("dataset_version", "-") for r in manifest})))

    r = subprocess.run([sys.executable, str(VERIFY_SCRIPT)], cwd=PROJECT_ROOT, capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or ["(출력 없음)"])[-1].strip()
    add("09 data/yolo 검증", "종료 코드 0", f"종료 코드 {r.returncode} · {last}", ok=(r.returncode == 0))
    return checks


def write_metrics(metrics, names: dict, n_images: int, weight_sha: str, cfg: dict,
                  model_name: str = "baseline_v1", out_csv: Path = METRICS_CSV) -> list[dict]:
    """reports/baseline_metrics.csv : all 1행 + Class 0~6 (Instance 0 Class 는 값 비우고 이유 기록).
    개선 실험 단계 15_evaluate_experiment.py 가 model_name · out_csv 만 바꿔 같은 함수로 Improved 를 기록한다 (같은 채점 코드)."""
    base = {"model": model_name, "weight_sha": weight_sha, "dataset_version": cfg.get("dataset_version", "kimchi_v1"),
            "split": SPLIT, "imgsz": cfg.get("imgsz", 640)}
    p, r, m50, m = metrics.box.mean_results()
    rows = [{**base, "class_id": "all", "class_name": "all", "images": n_images,
             "instances": int(metrics.nt_per_class.sum()), "precision": p, "recall": r, "map50": m50, "map50_95": m,
             "note": "Val 전체 (Ultralytics 기본 conf 0.001 · iou 0.7)"}]
    index = {int(c): i for i, c in enumerate(metrics.ap_class_index)}
    for cid in sorted(names):
        row = {**base, "class_id": cid, "class_name": names[cid],
               "images": int(metrics.nt_per_image[cid]), "instances": int(metrics.nt_per_class[cid])}
        if cid in index:
            cp, cr, c50, c = metrics.class_result(index[cid])
            row.update(precision=cp, recall=cr, map50=c50, map50_95=c, note="")
        else:
            row.update(precision="", recall="", map50="", map50_95="",
                       note=UNUSED_CLASSES.get(cid, "Val 에 Instance 0 → 해석 불가"))
        rows.append(row)
    for row in rows:
        for k in ("precision", "recall", "map50", "map50_95"):
            if row[k] != "":
                row[k] = f"{float(row[k]):.4f}"
    out_csv.parent.mkdir(exist_ok=True)
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return rows


def copy_figures(train_dir: Path, val_dir: Path, prefix: str = "baseline") -> list[str]:
    """그래프만 reports/figures/ 로 복사 (회사 이미지가 들어간 그림은 복사하지 않음). prefix: baseline / exp001"""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    pairs = [(train_dir / "results.png", f"{prefix}_results.png"),
             (val_dir / "confusion_matrix.png", f"{prefix}_confusion_matrix.png"),
             (val_dir / "confusion_matrix_normalized.png", f"{prefix}_confusion_matrix_normalized.png")]
    missing = []
    for src, dst in pairs:
        if src.exists():
            shutil.copy2(src, FIG_DIR / dst)
        else:
            missing.append(str(src.relative_to(PROJECT_ROOT)))
    return missing


def read_gt(stem: str) -> list[tuple]:
    path = VAL_LABELS / f"{stem}.txt"
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 5:
            out.append((int(parts[0]), *map(float, parts[1:])))
    return out


def is_small(box, size) -> bool:
    """모델 입력(긴 변 imgsz=640)으로 줄였을 때 32×32px 미만이면 작은 객체."""
    w_img, h_img = size
    scale = 640 / max(w_img, h_img)
    return (box[3] * w_img * scale) * (box[4] * h_img * scale) < SMALL_PX * SMALL_PX


def image_check(conf: float, imgsz: int, names: dict, best_pt: Path = BEST_PT,
                run_name: str = PRED_RUN_NAME, out_csv: Path = IMAGE_CHECK_CSV) -> tuple[list[dict], dict]:
    """Val 예측 → 이미지별 TP · FP · FN (Failure Analysis 후보 목록).
    작은 객체 기준(is_small)은 모델 imgsz 와 상관없이 640 기준으로 고정 → Baseline · Improved 가 같은 GT 묶음으로 비교된다."""
    val_rows = {r["file_name"]: r for r in read_manifest(MANIFEST_DIR / "val.csv")[0]}
    per_class = {c: {"gt": 0, "tp": 0, "fn": 0, "fp": 0} for c in names}
    rows = []
    for name, size, preds in predict_images(str(best_pt), VAL_IMAGES, conf, imgsz, RUNS_DIR / "predict", run_name):
        gts = read_gt(Path(name).stem)
        m = match_boxes(gts, preds, IOU_MATCH)
        small = [i for i, g in enumerate(gts) if is_small(g, size)]
        for i, g in enumerate(gts):
            per_class[g[0]]["gt"] += 1
            per_class[g[0]]["fn" if i in m["fn_idx"] else "tp"] += 1
        for c in m["fp_cls"]:
            per_class.setdefault(c, {"gt": 0, "tp": 0, "fn": 0, "fp": 0})["fp"] += 1
        info = val_rows.get(name, {})
        rows.append({
            "file_name": name, "scene_type": info.get("scene_type", "-"), "capture_group": info.get("capture_group", "-"),
            "gt": len(gts), "pred": len(preds), "tp": m["tp"], "fp": m["fp"], "fn": m["fn"],
            "class_err": m["class_err"], "small_gt": len(small), "small_fn": len(set(small) & set(m["fn_idx"])),
            "class4_pred": sum(p[0] == 4 for p in preds),
            "max_conf": f"{max((p[1] for p in preds), default=0):.3f}",
            "suspect": "yes" if (m["fp"] or m["fn"]) else "no",
        })
    rows.sort(key=lambda r: (-(r["fn"] + r["fp"]), r["file_name"]))
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return rows, per_class


def write_class_check(per_class: dict, names: dict, weight_sha: str, conf: float,
                      model_name: str = "baseline_v1", out_csv: Path = CLASS_CHECK_CSV) -> None:
    """reports/baseline_class_check.csv : conf 기준(현장에서 실제로 쓸 문턱)의 Class별 TP · FN · FP.

    baseline_metrics.csv 의 P · R 은 Ultralytics 가 고른 문턱 기준이라, 공장에서 쓸 conf 0.25 기준
    "몇 개 놓쳤나(FN)" 는 이 표로 본다. Improved 모델도 같은 표를 만들어 나란히 비교한다.
    """
    rows = []
    for c in sorted(per_class):
        v = per_class[c]
        rows.append({
            "model": model_name, "weight_sha": weight_sha, "split": SPLIT, "conf": conf, "iou": IOU_MATCH,
            "class_id": c, "class_name": names.get(c, "?"), "gt": v["gt"], "tp": v["tp"], "fn": v["fn"], "fp": v["fp"],
            "recall_at_conf": f"{v['tp'] / v['gt']:.4f}" if v["gt"] else "",            # 정답 중 찾은 비율
            "precision_at_conf": f"{v['tp'] / (v['tp'] + v['fp']):.4f}" if (v["tp"] + v["fp"]) else "",
            "note": UNUSED_CLASSES.get(c, "") if not v["gt"] else "",
        })
    tot = {k: sum(r[k] for r in rows) for k in ("gt", "tp", "fn", "fp")}
    rows.insert(0, {**{k: rows[0][k] for k in ("model", "weight_sha", "split", "conf", "iou")},
                    "class_id": "all", "class_name": "all", **tot,
                    "recall_at_conf": f"{tot['tp'] / tot['gt']:.4f}" if tot["gt"] else "",
                    "precision_at_conf": f"{tot['tp'] / (tot['tp'] + tot['fp']):.4f}" if (tot["tp"] + tot["fp"]) else "",
                    "note": f"conf {conf} · IoU ≥ {IOU_MATCH} · 같은 Class 짝짓기 (match_boxes)"})
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Baseline Validation 평가 · 이미지 Detection")
    parser.add_argument("--conf", type=float, default=0.25, help="예측 이미지 · FP/FN 집계용 conf (기본 0.25)")
    args = parser.parse_args()

    cfg = yaml.safe_load(BASELINE_YAML.read_text(encoding="utf-8")) if BASELINE_YAML.exists() else {}
    train_name = cfg.get("name", "baseline_v1")
    imgsz, batch = int(cfg.get("imgsz", 640)), int(cfg.get("batch", 16))

    checks = pre_checks(cfg, train_name)
    print("=== 평가 전 검사 ===")
    for c in checks:
        print(f"  {c['result']}  {c['item']:<34} 기대 {c['expected']} / 실제 {c['actual']}")
    n_fail = sum(c["result"] == "FAIL" for c in checks)
    print(f"  → PASS {len(checks) - n_fail} / FAIL {n_fail}")
    if n_fail:
        sys.exit("\n[중단] FAIL 이 있어 평가하지 않았습니다. (학습 완료 · 조건 문서 · Weight 를 먼저 확인)")

    # ① Validation 지표 ──────────────────────────────────────────────────────
    print(f"\n=== ① Validation 평가 (split=val · imgsz {imgsz} · batch {batch}) ===")
    metrics, val_dir = evaluate_detector(str(BEST_PT), str(DATASET_YAML), SPLIT, imgsz, batch, RUNS_DIR, VAL_RUN_NAME)
    names = {int(k): v for k, v in metrics.names.items()}
    n_images = len(list(VAL_IMAGES.glob("*.jpg")))
    rows = write_metrics(metrics, names, n_images, sha12(BEST_PT), cfg)

    # ② 그림 정리 ────────────────────────────────────────────────────────────
    missing = copy_figures(RUNS_DIR / train_name, val_dir)

    # ③ Val 예측 · 이미지별 FP / FN ────────────────────────────────────────────
    print(f"\n=== ③ Val 예측 (conf {args.conf}) · 이미지별 FP / FN ===")
    img_rows, per_class = image_check(args.conf, imgsz, names)
    write_class_check(per_class, names, sha12(BEST_PT), args.conf)

    # ── 출력 ────────────────────────────────────────────────────────────────
    print("\n=== Baseline Validation 지표 (reports/baseline_metrics.csv) ===")
    print(f"  {'class':<24}{'inst':>6}{'P':>8}{'R':>8}{'mAP50':>8}{'50-95':>8}  비고")
    for r in rows:
        print(f"  {str(r['class_id']) + ' ' + r['class_name']:<24}{r['instances']:>6}{r['precision'] or '-':>8}"
              f"{r['recall'] or '-':>8}{r['map50'] or '-':>8}{r['map50_95'] or '-':>8}  {r['note']}")

    print(f"\n=== Class별 TP · FN · FP (conf {args.conf} · IoU ≥ {IOU_MATCH}) ===")
    print(f"  {'class':<24}{'GT':>5}{'TP':>5}{'FN':>5}{'FP':>5}")
    for c in sorted(per_class):
        v = per_class[c]
        print(f"  {str(c) + ' ' + names.get(c, '?'):<24}{v['gt']:>5}{v['tp']:>5}{v['fn']:>5}{v['fp']:>5}")

    sus = [r for r in img_rows if r["suspect"] == "yes"]
    small_gt, small_fn = sum(r["small_gt"] for r in img_rows), sum(r["small_fn"] for r in img_rows)
    print(f"\n  실패 의심 이미지 {len(sus)} / {len(img_rows)}장 (FP 또는 FN ≥ 1) · 위에서부터 FP+FN 많은 순")
    for r in sus[:10]:
        print(f"    {r['file_name']}  GT {r['gt']} · 예측 {r['pred']} · FN {r['fn']} · FP {r['fp']} "
              f"(Class 오류 {r['class_err']}) · {r['capture_group']}")
    print(f"  작은 객체(입력 640 기준 {SMALL_PX}px 미만) GT {small_gt}개 중 FN {small_fn}개")
    print(f"  Class 4 예측 {sum(r['class4_pred'] for r in img_rows)}개 (데이터 0건 → 있으면 전부 FP 후보)")
    print("  정상 김치(normal_kimchi) 0장 → 정상 김치 FP 는 이 데이터로 확인 불가 (README 16장 한계)")

    print("\n=== 저장 ===")
    for p in (METRICS_CSV, FIG_DIR / "baseline_results.png", FIG_DIR / "baseline_confusion_matrix.png",
              FIG_DIR / "baseline_confusion_matrix_normalized.png", IMAGE_CHECK_CSV, CLASS_CHECK_CSV):
        print(f"  {'OK ' if p.exists() else '없음'} {p.relative_to(PROJECT_ROOT)}")
    print(f"  (Git 제외) {val_dir.relative_to(PROJECT_ROOT)}/ · runs/predict/{PRED_RUN_NAME}/  ← 박스 그린 Val 이미지는 여기서 눈으로 확인")

    print("\n=== Baseline 평가 단계 Daily Gate ===")
    print(f"  {'✅' if METRICS_CSV.exists() else '☐'} baseline_metrics.csv 에 실제 Val P · R · mAP50 · mAP50-95 기록")
    print("  ✅ Class별 성능 확인 (위 표 · Class 4 는 Instance 0)")
    print(f"  {'✅' if not missing else '☐'} reports/figures/ 학습곡선 · Confusion Matrix" + (f" (없음: {missing})" if missing else ""))
    print("  ☐ 실제 Val Prediction 이미지 확인 ← 사람이 runs/predict/baseline_val_images/ 를 열어 보고 체크")
    print(f"  ✅ 정상 김치 FP(데이터 0장 · 한계 기록) · 작은 객체 FN({small_fn}/{small_gt}) 확인")
    print(f"  ✅ 실패 의심 이미지 {len(sus)}장 → reports/baseline_val_image_check.csv (실패 분석 단계 입력)")
    print("  ✅ Frozen Test · Bridge Holdout 미사용 (split=val 고정 · test 평가 거부)")
    four = [BEST_PT, METRICS_CSV, CONDITION_MD, PROJECT_ROOT / "reports" / "baseline_results.csv"]
    print(f"  {'✅' if all(p.exists() for p in four) else '☐'} 산출물 2 네 파일: baseline_best.pt · baseline_metrics.csv · "
          "baseline_training_condition.md · results.csv (사본 reports/baseline_results.csv)")
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
