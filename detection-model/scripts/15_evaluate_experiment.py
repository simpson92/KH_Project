"""개선 실험 단계: 개선 실험 Validation 평가 · Baseline 과 비교 (요구사항 §20.6 · 산출물 5).

사용법 (detection-model 폴더에서 · 14_train_experiment.py 학습이 "완료" 된 뒤):
    python scripts/15_evaluate_experiment.py --config configs/exp001.yaml

핵심: Baseline 을 채점한 11 의 함수를 "그대로" 불러 쓴다 → 같은 Val 74장 · 같은 conf 0.25 · 같은 짝짓기 · 같은 작은 객체 기준.
      바뀌는 것은 가중치 파일과 (그 모델이 학습한) imgsz 뿐이다.

결과 (Git):
    reports/exp001_metrics.csv                    Val 전체 + Class별 P · R · mAP (Ultralytics · baseline_metrics.csv 와 같은 형식)
    reports/exp001_class_check.csv                conf 0.25 Class별 GT · TP · FN · FP (baseline_class_check.csv 와 같은 형식)
    reports/exp001_val_image_check.csv            이미지별 TP · FP · FN · 작은 객체 FN
    reports/figures/exp001_results.png · exp001_confusion_matrix(_normalized).png   그래프만
    reports/experiment_log.csv                    baseline_v1 · exp001 한 줄씩 (필드 · decision 칸은 사람이 씀)
    reports/baseline_vs_improved.md               처음 한 번만 숫자 초안 생성 (해석 · 결정은 사람이 씀 · 이미 있으면 덮어쓰지 않음)
결과 (Git 제외):
    runs/exp001_val/ · runs/predict/exp001_val_images/
"""
from pathlib import Path
import argparse
import csv
import importlib.util
import re
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from src.manifest import read_manifest
from src.evaluate_detector import evaluate_detector
from src.train_detector import TRAIN_KEYS

# 11 (Baseline 채점 코드)를 그대로 가져온다 → 채점 방법이 두 모델에서 완전히 같다
_spec = importlib.util.spec_from_file_location("eval11", PROJECT_ROOT / "scripts" / "11_evaluate_baseline.py")
e11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e11)

REPORTS = PROJECT_ROOT / "reports"
RUNS_DIR = PROJECT_ROOT / "runs"
DATASET_YAML = PROJECT_ROOT / "configs" / "dataset.yaml"
BASELINE_YAML = PROJECT_ROOT / "configs" / "baseline.yaml"
LOG_CSV = REPORTS / "experiment_log.csv"
COMPARE_MD = REPORTS / "baseline_vs_improved.md"
CONF = 0.25
LOG_FIELDS = ["experiment_id", "date", "dataset_version", "model", "imgsz", "epochs", "batch", "seed",
              "changed_variable", "reason", "validation_precision", "validation_recall", "validation_map50",
              "validation_map50_95", "recall_at_conf025", "fn_at_conf025", "small_fn", "weight_sha", "decision"]


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def md_info(md: Path, weight_name: str) -> dict:
    text = md.read_text(encoding="utf-8") if md.exists() else ""
    st = re.search(r"\*\*상태\*\*: ([^·\n]+)", text)
    sha = re.search(re.escape(weight_name) + r"` · sha `([0-9a-f]{12})`", text)
    date = re.search(r"학습 시작 · 종료 \| (\d{4}-\d{2}-\d{2})", text)
    return {"state": st.group(1).strip() if st else "문서 없음", "sha": sha.group(1) if sha else "-",
            "date": date.group(1) if date else "-"}


def pre_checks(cfg, base, best, md) -> list[dict]:
    checks = []

    def add(item, expected, actual, ok=None):
        ok = (str(expected) == str(actual)) if ok is None else ok
        checks.append({"item": item, "expected": expected, "actual": actual, "result": "PASS" if ok else "FAIL"})

    try:
        import ultralytics
        ver = ultralytics.__version__
    except ImportError:
        ver = "없음"
    add("Ultralytics 버전 (팀 고정)", str(cfg["ultralytics_version"]), ver)
    info = md_info(md, best.name)
    add(f"{cfg['name']} 학습 상태 (condition md)", "완료", info["state"])
    add("Improved Weight 있음", "있음", "있음" if best.exists() else "없음")
    add("Weight sha = 학습 기록", info["sha"], e11.sha12(best) if best.exists() else "-")
    add("학습곡선 원본 있음", f"runs/{cfg['name']}/results.png",
        f"runs/{cfg['name']}/results.png" if (RUNS_DIR / cfg["name"] / "results.png").exists() else "없음")
    data_yaml = yaml.safe_load(DATASET_YAML.read_text(encoding="utf-8"))
    add("dataset.yaml 에 Bridge 없음", "no", "yes" if "bridge" in " ".join(str(data_yaml.get(k, "")) for k in ("train", "val", "test")) else "no")
    _, schema = read_manifest(PROJECT_ROOT / "manifests" / "split_manifest.csv")
    add("manifest 스키마", "v2", schema)
    add("Dataset Version = Baseline", base["dataset_version"], cfg["dataset_version"])
    r = subprocess.run([sys.executable, str(e11.VERIFY_SCRIPT)], cwd=PROJECT_ROOT, capture_output=True, text=True)
    add("09 data/yolo 검증", "종료 코드 0", f"종료 코드 {r.returncode}", ok=(r.returncode == 0))
    need = ["baseline_metrics.csv", "baseline_class_check.csv", "baseline_val_image_check.csv"]
    miss = [n for n in need if not (REPORTS / n).exists()]
    add("비교 기준 Baseline 결과 3개", "있음", "있음" if not miss else f"없음 {miss}", ok=not miss)
    return checks


def update_log(cfg, base, exp_all, exp_cls, exp_small_fn, exp_sha, exp_date, changed):
    """experiment_log.csv: baseline_v1 · 이번 실험을 한 줄씩. 사람이 쓴 decision 칸은 지우지 않는다."""
    old = {r["experiment_id"]: r for r in read_csv(LOG_CSV)} if LOG_CSV.exists() else {}
    b_all = next(r for r in read_csv(REPORTS / "baseline_metrics.csv") if r["class_id"] == "all")
    b_cls = next(r for r in read_csv(REPORTS / "baseline_class_check.csv") if r["class_id"] == "all")
    b_small = sum(int(r["small_fn"]) for r in read_csv(REPORTS / "baseline_val_image_check.csv"))
    b_info = md_info(REPORTS / "baseline_training_condition.md", "baseline_best.pt")

    def row(eid, c, date, changed_var, reason, m_all, m_cls, small, sha, default_decision):
        return {"experiment_id": eid, "date": date, "dataset_version": c["dataset_version"], "model": c["model"],
                "imgsz": c["imgsz"], "epochs": c["epochs"], "batch": c["batch"], "seed": c["seed"],
                "changed_variable": changed_var, "reason": reason,
                "validation_precision": m_all["precision"], "validation_recall": m_all["recall"],
                "validation_map50": m_all["map50"], "validation_map50_95": m_all["map50_95"],
                "recall_at_conf025": m_cls["recall_at_conf"], "fn_at_conf025": m_cls["fn"], "small_fn": small,
                "weight_sha": sha, "decision": old.get(eid, {}).get("decision") or default_decision}

    rows = {**old}
    rows[base["name"]] = row(base["name"], base, b_info["date"], "-", "팀 공통 기준 모델 (Baseline 학습 단계)", b_all, b_cls, b_small,
                             b_info["sha"], "기준")
    rows[cfg["name"]] = row(cfg["name"], cfg, exp_date, changed, cfg.get("reason", ""), exp_all, exp_cls, exp_small_fn,
                            exp_sha, "")
    with open(LOG_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows.values())


def fmt_delta(a, b, digits=3, lower_better=False):
    d = float(b) - float(a)
    good = (d < 0) if lower_better else (d > 0)
    mark = "▲" if d > 0 else ("▼" if d < 0 else "=")
    return f"{mark}{abs(d):.{digits}f}" + (" ✓" if good and d != 0 else "")


def main():
    parser = argparse.ArgumentParser(description="개선 실험 Val 평가 · Baseline 비교")
    parser.add_argument("--config", required=True, help="실험 설정 (예: configs/exp001.yaml)")
    args = parser.parse_args()

    cfg = yaml.safe_load((PROJECT_ROOT / args.config).read_text(encoding="utf-8"))
    base = yaml.safe_load(BASELINE_YAML.read_text(encoding="utf-8"))
    name = cfg["name"]
    best = PROJECT_ROOT / "models" / "improved" / f"{name}_best.pt"
    md = REPORTS / f"{name}_training_condition.md"
    imgsz, batch = int(cfg["imgsz"]), int(cfg["batch"])
    changed = " · ".join(f"{k} {base.get(k)} → {cfg.get(k)}" for k in [*TRAIN_KEYS, "model"]
                         if base.get(k) != cfg.get(k)) or "-"          # 14 와 같은 방법으로 "바꾼 것" 계산

    checks = pre_checks(cfg, base, best, md)
    print("=== 평가 전 검사 ===")
    for c in checks:
        print(f"  {c['result']}  {c['item']:<34} 기대 {c['expected']} / 실제 {c['actual']}")
    n_fail = sum(c["result"] == "FAIL" for c in checks)
    print(f"  → PASS {len(checks) - n_fail} / FAIL {n_fail}")
    if n_fail:
        sys.exit("\n[중단] FAIL 이 있어 평가하지 않았습니다.")

    # ① Val 지표 (11 과 같은 함수 · imgsz 는 이 모델이 학습한 값) ───────────────────────────
    print(f"\n=== ① {name} Validation 평가 (split=val · imgsz {imgsz} · batch {batch}) ===")
    metrics, val_dir = evaluate_detector(str(best), str(DATASET_YAML), "val", imgsz, batch, RUNS_DIR, f"{name}_val")
    names = {int(k): v for k, v in metrics.names.items()}
    n_images = len(list(e11.VAL_IMAGES.glob("*.jpg")))
    sha = e11.sha12(best)
    rows = e11.write_metrics(metrics, names, n_images, sha, cfg, model_name=name, out_csv=REPORTS / f"{name}_metrics.csv")
    missing = e11.copy_figures(RUNS_DIR / name, val_dir, prefix=name)

    # ② conf 0.25 이미지별 · Class별 (11 과 같은 함수) ────────────────────────────────────────
    print(f"\n=== ② {name} Val 예측 (conf {CONF}) · 이미지별 · Class별 ===")
    img_rows, per_class = e11.image_check(CONF, imgsz, names, best_pt=best, run_name=f"{name}_val_images",
                                          out_csv=REPORTS / f"{name}_val_image_check.csv")
    e11.write_class_check(per_class, names, sha, CONF, model_name=name, out_csv=REPORTS / f"{name}_class_check.csv")

    # ③ 비교 ────────────────────────────────────────────────────────────────────────
    b_all = next(r for r in read_csv(REPORTS / "baseline_metrics.csv") if r["class_id"] == "all")
    b_cls = {r["class_id"]: r for r in read_csv(REPORTS / "baseline_class_check.csv")}
    e_cls = {r["class_id"]: r for r in read_csv(REPORTS / f"{name}_class_check.csv")}
    b_img = {r["file_name"]: r for r in read_csv(REPORTS / "baseline_val_image_check.csv")}
    e_img = {r["file_name"]: r for r in img_rows}
    e_all = rows[0]
    b_small, e_small = sum(int(r["small_fn"]) for r in b_img.values()), sum(int(r["small_fn"]) for r in img_rows)
    small_gt = sum(int(r["small_gt"]) for r in b_img.values())
    update_log(cfg, base, e_all, e_cls["all"], e_small, sha, md_info(md, best.name)["date"], changed)

    print(f"\n=== Baseline vs {name} (같은 Val 74장) — 바꾼 것: {changed} ===")
    print(f"  {'지표':<26}{'baseline_v1':>12}{name:>12}   변화")
    for k, label in [("precision", "P (Ultralytics)"), ("recall", "R (Ultralytics)"), ("map50", "mAP50"), ("map50_95", "mAP50-95")]:
        print(f"  {label:<26}{b_all[k]:>12}{e_all[k]:>12}   {fmt_delta(b_all[k], e_all[k])}")
    print(f"  {'Recall (conf 0.25)':<26}{b_cls['all']['recall_at_conf']:>12}{e_cls['all']['recall_at_conf']:>12}   "
          f"{fmt_delta(b_cls['all']['recall_at_conf'], e_cls['all']['recall_at_conf'])}")
    print(f"  {'FN 놓침 (conf 0.25)':<26}{b_cls['all']['fn']:>12}{e_cls['all']['fn']:>12}   {fmt_delta(b_cls['all']['fn'], e_cls['all']['fn'], 0, True)}")
    print(f"  {'FP 오검출 (conf 0.25)':<26}{b_cls['all']['fp']:>12}{e_cls['all']['fp']:>12}   {fmt_delta(b_cls['all']['fp'], e_cls['all']['fp'], 0, True)}")
    print(f"  {'작은 객체 FN (/' + str(small_gt) + ')':<26}{b_small:>12}{e_small:>12}   {fmt_delta(b_small, e_small, 0, True)}")
    print("\n  Class별 conf 0.25 (FN · FP)            baseline         " + name)
    for cid in [c for c in b_cls if c != "all"]:
        b, e = b_cls[cid], e_cls.get(cid, {})
        if int(b["gt"]) == 0 and int(e.get("fp", 0) or 0) == 0:
            continue
        print(f"    {cid} {b['class_name']:<24} GT {b['gt']:>4}   FN {b['fn']:>4} · FP {b['fp']:>3}   →   FN {e.get('fn', '-'):>4} · FP {e.get('fp', '-'):>3}")

    fa = REPORTS / "failure_analysis.csv"
    if fa.exists():
        seen = list(dict.fromkeys(r["image"].strip() for r in read_csv(fa)))
        print("\n  실패 분석 단계 대표 실패 사진 (FN · FP)          baseline   →   " + name)
        for n in seen:
            if n in b_img and n in e_img:
                print(f"    {n:<28} FN {b_img[n]['fn']:>2} · FP {b_img[n]['fp']:>2}   →   FN {e_img[n]['fn']:>2} · FP {e_img[n]['fp']:>2}")

    if not COMPARE_MD.exists():                       # 처음 한 번만 숫자 초안 (사람이 쓴 해석은 덮어쓰지 않음)
        L = [f"# Baseline vs Improved ({name}) — 같은 Validation 비교", "",
             "> **상태**: 초안 (숫자는 `15_evaluate_experiment.py` 자동 · 해석 · 결정은 팀이 작성)", "",
             "## 1. 비교 조건", "", "| 항목 | baseline_v1 | " + name + " |", "|---|---|---|",
             f"| 바꾼 것 | — | **{changed}** |",
             f"| Dataset Version · Val | {base['dataset_version']} · Val 74장 | 같음 |",
             f"| 가중치 sha | {md_info(REPORTS / 'baseline_training_condition.md', 'baseline_best.pt')['sha']} | {sha} |",
             "| 채점 코드 | 11 (conf 0.25 · IoU 0.5 · 작은 객체 640 기준 32px) | 같은 함수 (15 가 11 을 불러 씀) |", "",
             "## 2. 지표", "", "| 지표 | baseline_v1 | " + name + " | 변화 |", "|---|---|---|---|"]
        for k, label in [("precision", "P"), ("recall", "R"), ("map50", "mAP50"), ("map50_95", "mAP50-95")]:
            L.append(f"| {label} (Ultralytics) | {b_all[k]} | {e_all[k]} | {fmt_delta(b_all[k], e_all[k])} |")
        L += [f"| Recall (conf 0.25) | {b_cls['all']['recall_at_conf']} | {e_cls['all']['recall_at_conf']} | "
              f"{fmt_delta(b_cls['all']['recall_at_conf'], e_cls['all']['recall_at_conf'])} |",
              f"| FN (conf 0.25) | {b_cls['all']['fn']} | {e_cls['all']['fn']} | {fmt_delta(b_cls['all']['fn'], e_cls['all']['fn'], 0, True)} |",
              f"| FP (conf 0.25) | {b_cls['all']['fp']} | {e_cls['all']['fp']} | {fmt_delta(b_cls['all']['fp'], e_cls['all']['fp'], 0, True)} |",
              f"| 작은 객체 FN (/{small_gt}) | {b_small} | {e_small} | {fmt_delta(b_small, e_small, 0, True)} |", "",
              "## 3. 실패 분석 단계 핵심 FP / FN 패턴은 어떻게 바뀌었나", "",
              "- H1 작은 이물 놓침: (작은 객체 FN · 플라스틱 FN 숫자로 작성)",
              "- H2 갈변: (갈변 FN 6개 중 몇 개를 찾았나)",
              "- H3 branch 오검출: (branch FP 30 → ?)",
              "- 나빠진 것도 적기: (FP 증가 · 특정 Class 하락 등)", "",
              "## 4. 결론 · Final Model 후보 (Frozen Test 를 보지 않고 결정)", "",
              "- 후보: ☐ baseline_v1 / ☐ " + name,
              "- 이유: ", "- 위험 · 한계: ", ""]
        COMPARE_MD.write_text("\n".join(L), encoding="utf-8")
        print(f"\n  reports/baseline_vs_improved.md 초안을 만들었습니다 (3 · 4장은 팀이 작성)")

    print("\n=== 저장 ===")
    for p in [REPORTS / f"{name}_metrics.csv", REPORTS / f"{name}_class_check.csv", REPORTS / f"{name}_val_image_check.csv",
              e11.FIG_DIR / f"{name}_results.png", e11.FIG_DIR / f"{name}_confusion_matrix.png", LOG_CSV, COMPARE_MD]:
        print(f"  {'OK ' if p.exists() else '없음'} {p.relative_to(PROJECT_ROOT)}")
    if missing:
        print(f"  (그림 없음: {missing})")

    print("\n=== 개선 실험 단계 Daily Gate ===")
    print("  ✅ 실패 분석 단계와 연결된 주요 변수 하나만 변경 (14 가 학습 전에 확인)")
    print(f"  {'✅' if best.exists() else '☐'} models/improved/{best.name} 보관")
    print("  ✅ experiment_log.csv 에 실제 조건 · Val 결과 기록  ← decision 칸은 팀이 작성")
    print("  ✅ Baseline 과 같은 Dataset Version · Validation")
    print(f"  {'✅' if not missing else '☐'} reports/figures/ 에 {name} 학습곡선 · Confusion Matrix")
    print("  ☐ baseline_vs_improved.md 에서 성능 · 핵심 FP/FN 비교 (3 · 4장 사람이 작성)")
    print("  ☐ 좋아졌든 나빠졌든 기록 · ☐ Frozen Test 를 보지 않고 Final Model 후보 결정 (회의)")


if __name__ == "__main__":
    main()
