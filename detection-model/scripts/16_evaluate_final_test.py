"""Final 선정 단계: Final Model 의 Frozen Test 최종평가 — 딱 1회 (산출물 5).

사용법 (detection-model 폴더에서 · venv 켠 뒤 · final_model_selection.md 를 커밋한 뒤):
    python scripts/16_evaluate_final_test.py --dry-run     # ① 평가 전 검사만 (Test 를 열지 않음 · 몇 초)
    python scripts/16_evaluate_final_test.py               # ② Frozen Test 1회 평가 → 기록

※ 요구사항 문서의 이름은 11_evaluate_final_test.py 이지만, 번호는 실행 순서대로 매겼다 (README 6.2 실행표).

순서 (요구사항 §21.A — 반드시 이 순서):
    Validation 근거로 Final Model 선택 (reports/final_model_selection.md · 상태: 확정 · 커밋)
        ↓
    models/final/final_best.pt (sha 가 선택 문서 · 원본 실험 기록과 같아야 함)
        ↓
    그다음에만 Frozen Test  ← 이 스크립트

입력:
    reports/final_model_selection.md     "**상태: 확정**" · Final Weight sha · 원본 설정(configs/exp001.yaml) — 커밋돼 있어야 함
    models/final/final_best.pt           Final Weight (Git 제외)
    configs/dataset.yaml · data/yolo/{images,labels}/test   Frozen Test 80장 (지문 4f9291849fe6)

결과 (Git):
    reports/final_metrics.csv            Frozen Test 전체 + Class별 P · R · mAP50 · mAP50-95 (Ultralytics · baseline_metrics.csv 와 같은 형식)
    reports/final_class_check.csv        conf 0.25 Class별 GT · TP · FN · FP (Val 과 같은 채점 함수)
    reports/final_test_image_check.csv   이미지별 TP · FP · FN · 작은 객체 FN (후속 프로젝트 인계 의 대표 FP/FN 근거)
    reports/final_test_runs.csv          언제 · 어떤 weight · 몇 번 평가했나 (1회 증거)
    reports/figures/final_test_confusion_matrix(_normalized).png · final_test_pr_curve.png   그래프만
결과 (Git 제외):
    runs/final_test/ · runs/predict/final_test_images/   (회사 사진이 들어간 그림)

원칙:
    - 채점은 11 의 함수를 그대로 쓴다 (같은 conf 0.25 · IoU 0.5 · 짝짓기 · 작은 객체 640 기준) → Val 숫자와 나란히 비교 가능.
    - imgsz 는 Final Model 이 학습한 값 (원본 설정 yaml · exp001 = 1280).
    - 1회 잠금: reports/final_metrics.csv 가 이미 있으면 실행을 거부한다.
      기술적 오류(전원 · OOM 등)로 결과를 못 남긴 경우에만 issue_log 에 이유를 적고 팀 확인 후 --rerun-reason "이유" 로 다시 실행.
    - Test 결과를 보고 Final Model 을 바꾸거나 다시 학습하지 않는다. 낮게 나와도 그대로 기록한다.
"""
from pathlib import Path
from datetime import datetime
import argparse
import csv
import importlib.util
import re
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from src.manifest import read_manifest, fingerprint
from src.evaluate_detector import evaluate_detector


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / "scripts" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


e11 = _load("eval11", "11_evaluate_baseline.py")      # 채점 함수 (Val 과 같은 코드)
t10 = _load("train10", "10_train_baseline.py")        # git · sha 도우미

REPORTS = PROJECT_ROOT / "reports"
RUNS_DIR = PROJECT_ROOT / "runs"
FIG_DIR = REPORTS / "figures"
DATASET_YAML = PROJECT_ROOT / "configs" / "dataset.yaml"
SELECTION_MD = REPORTS / "final_model_selection.md"
FINAL_PT = PROJECT_ROOT / "models" / "final" / "final_best.pt"
TEST_IMAGES = PROJECT_ROOT / "data" / "yolo" / "images" / "test"
TEST_LABELS = PROJECT_ROOT / "data" / "yolo" / "labels" / "test"
TEST_MANIFEST = PROJECT_ROOT / "manifests" / "test.csv"
METRICS_CSV = REPORTS / "final_metrics.csv"
CLASS_CSV = REPORTS / "final_class_check.csv"
IMAGE_CSV = REPORTS / "final_test_image_check.csv"
RUNS_LOG = REPORTS / "final_test_runs.csv"
FROZEN_TEST_FP = "4f9291849fe6"                      # split_policy.md 8장
CONF = 0.25
RUN_NAME = "final_test"


def selection_info() -> dict:
    """final_model_selection.md 에서 상태 · Final sha · 원본 Weight · 원본 설정을 읽는다."""
    text = SELECTION_MD.read_text(encoding="utf-8") if SELECTION_MD.exists() else ""
    fsha = re.search(r"final_best\.pt` · sha `([0-9a-f]{12})`", text)
    src = re.search(r"원본 Weight \| `models/improved/([\w-]+)_best\.pt` · sha `([0-9a-f]{12})`", text)
    cfg = re.search(r"원본 설정 \| `(configs/[\w.-]+\.yaml)`", text)
    return {"confirmed": "**상태: 확정**" in text, "exists": bool(text),
            "final_sha": fsha.group(1) if fsha else "-",
            "source": src.group(1) if src else "-", "source_sha": src.group(2) if src else "-",
            "config": cfg.group(1) if cfg else "-"}


def pre_checks(info: dict, cfg: dict, rerun_reason: str, mode: str) -> list[dict]:
    checks = []

    def add(item, expected, actual, ok=None, warn_ok=False):
        ok = (str(expected) == str(actual)) if ok is None else ok
        checks.append({"item": item, "expected": expected, "actual": actual,
                       "result": "PASS" if ok else ("WARN" if warn_ok else "FAIL")})

    try:
        import ultralytics
        ver = ultralytics.__version__
    except ImportError:
        ver = "없음"
    add("Ultralytics 버전 (팀 고정)", str(cfg.get("ultralytics_version", "8.4.175")), ver)

    # ── ① 선택이 먼저 (요구사항 §21.A) ───────────────────────────────────────────
    add("final_model_selection.md 확정", "**상태: 확정**",
        "**상태: 확정**" if info["confirmed"] else ("문서 없음" if not info["exists"] else "초안"))
    rel = str(SELECTION_MD.relative_to(PROJECT_ROOT))
    committed = bool(t10.git("log", "-1", "--format=%h", "--", rel)) and not t10.git("status", "--porcelain", "--", rel)
    add("선택 문서가 커밋됨 (Test 전에 결정한 기록)", "커밋됨", "커밋됨" if committed else "미커밋 또는 수정됨", ok=committed)

    # ── ② Final Weight = 선택 문서 = 원본 실험 기록 ────────────────────────────
    add("models/final/final_best.pt 있음", "있음", "있음" if FINAL_PT.exists() else "없음")
    sha = e11.sha12(FINAL_PT) if FINAL_PT.exists() else "-"
    add("Final sha = 선택 문서", info["final_sha"], sha)
    cond = REPORTS / f"{info['source']}_training_condition.md"
    m = re.search(re.escape(f"{info['source']}_best.pt") + r"` · sha `([0-9a-f]{12})`",
                  cond.read_text(encoding="utf-8") if cond.exists() else "")
    add(f"Final sha = {info['source']} 학습 기록", m.group(1) if m else "기록 없음", sha)
    add("평가 imgsz = 원본 설정", f"{info['config']} 의 imgsz", f"{cfg.get('imgsz', '-')}", ok=bool(cfg.get("imgsz")))

    # ── ③ 시험지가 봉인된 그 Frozen Test 인가 ────────────────────────────────
    data_yaml = yaml.safe_load(DATASET_YAML.read_text(encoding="utf-8"))
    add("dataset.yaml 에 test 경로", "images/test", data_yaml.get("test", "없음"))
    add("dataset.yaml 에 Bridge 없음", "no",
        "yes" if "bridge" in " ".join(str(data_yaml.get(k, "")) for k in ("train", "val", "test")) else "no")
    manifest, schema = read_manifest(PROJECT_ROOT / "manifests" / "split_manifest.csv")
    add("manifest 스키마", "v2", schema)
    test_names = [r["file_name"] for r in manifest if r["split"] == "test"]
    add("Frozen Test 지문 (Split 단계 봉인)", FROZEN_TEST_FP, fingerprint(test_names))
    n_img = len(list(TEST_IMAGES.glob("*.jpg"))) if TEST_IMAGES.exists() else 0
    add("Test 이미지 수 = manifest", len(test_names), n_img)
    r = subprocess.run([sys.executable, str(e11.VERIFY_SCRIPT)], cwd=PROJECT_ROOT, capture_output=True, text=True)
    add("09 data/yolo 검증", "종료 코드 0", f"종료 코드 {r.returncode}", ok=(r.returncode == 0))

    # ── ④ 1회 잠금 · 재현 ────────────────────────────────────────────────────
    done = METRICS_CSV.exists()
    add("Frozen Test 1회 잠금 (final_metrics.csv 없음)", "없음",
        "없음" if not done else ("있음 · 재실행 사유: " + rerun_reason if rerun_reason else "있음 (이미 평가함)"),
        ok=(not done) or bool(rerun_reason))
    dirty = t10.git("status", "--porcelain", "--", "configs", "src", "scripts", "manifests")
    add("configs · src · scripts · manifests 커밋됨", "변경 없음",
        "변경 없음" if not dirty else f"미커밋 {len(dirty.splitlines())}개", ok=not dirty, warn_ok=(mode == "dry"))
    return checks


def log_run(row: dict) -> None:
    new = not RUNS_LOG.exists()
    with open(RUNS_LOG, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row), lineterminator="\n")
        if new:
            w.writeheader()
        w.writerow(row)


def rewrite(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description="Frozen Test 최종평가 (1회)")
    parser.add_argument("--dry-run", action="store_true", help="평가 전 검사만 (Test 를 열지 않음)")
    parser.add_argument("--rerun-reason", default="", help="기술적 오류로 결과를 못 남겼을 때만 · issue_log 기록 · 팀 확인 후")
    args = parser.parse_args()
    mode = "dry" if args.dry_run else "run"

    info = selection_info()
    cfg_path = PROJECT_ROOT / info["config"]
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.is_file() else {}
    checks = pre_checks(info, cfg, args.rerun_reason, mode)
    print(f"=== Frozen Test 평가 전 검사 ({mode}) ===")
    for c in checks:
        print(f"  {c['result']}  {c['item']:<40} 기대 {c['expected']} / 실제 {c['actual']}")
    n_fail = sum(c["result"] == "FAIL" for c in checks)
    print(f"  → PASS {sum(c['result'] == 'PASS' for c in checks)} / WARN {sum(c['result'] == 'WARN' for c in checks)} / FAIL {n_fail}")
    if n_fail:
        sys.exit("\n[중단] FAIL 이 있어 Frozen Test 를 열지 않았습니다.")
    if mode == "dry":
        print("\n--dry-run: 검사만 했습니다 (Test 는 아직 열지 않음).")
        print("다음: 커밋 확인 → python scripts/16_evaluate_final_test.py   ← 단 한 번")
        return

    imgsz, batch = int(cfg["imgsz"]), int(cfg.get("batch", 16))
    sha = e11.sha12(FINAL_PT)
    code = t10.git("rev-parse", "--short", "HEAD") or "-"
    start = datetime.now()
    log_run({"time": f"{start:%Y-%m-%d %H:%M:%S}", "event": "시작", "weight": "models/final/final_best.pt",
             "weight_sha": sha, "source": info["source"], "imgsz": imgsz, "code": code,
             "reason": args.rerun_reason or "최초 1회"})

    # 11 의 채점 함수를 그대로 쓰되, 대상 폴더 · split 표시만 test 로 바꾼다 (채점 규칙은 그대로)
    e11.SPLIT, e11.VAL_IMAGES, e11.VAL_LABELS = "test", TEST_IMAGES, TEST_LABELS

    # ① 전체 · Class별 지표 (Ultralytics) ──────────────────────────────────────────
    print(f"\n=== ① Frozen Test 평가 (split=test · imgsz {imgsz} · batch {batch} · {info['source']}) ===")
    metrics, test_dir = evaluate_detector(str(FINAL_PT), str(DATASET_YAML), "test", imgsz, batch,
                                          RUNS_DIR, RUN_NAME, allow_test=True)
    names = {int(k): v for k, v in metrics.names.items()}
    n_images = len(list(TEST_IMAGES.glob("*.jpg")))
    rows = e11.write_metrics(metrics, names, n_images, sha, cfg, model_name="final", out_csv=METRICS_CSV)
    for r in rows:
        r["note"] = (f"Frozen Test 전체 (Ultralytics 기본 conf 0.001 · iou 0.7) · 원본 {info['source']} · 1회"
                     if r["class_id"] == "all" else r["note"].replace("Val 에", "Test 에"))
    rewrite(METRICS_CSV, rows)

    # ② conf 0.25 이미지별 · Class별 (Val 과 같은 함수) ───────────────────────────────
    print(f"\n=== ② Frozen Test 예측 (conf {CONF}) · 이미지별 · Class별 ===")
    img_rows, per_class = e11.image_check(CONF, imgsz, names, best_pt=FINAL_PT, run_name="final_test_images",
                                          out_csv=IMAGE_CSV)
    scene = {r["file_name"]: r for r in read_manifest(TEST_MANIFEST)[0]}       # 11 은 val.csv 를 보므로 test.csv 로 채움
    for r in img_rows:
        r["scene_type"] = scene.get(r["file_name"], {}).get("scene_type", "-")
        r["capture_group"] = scene.get(r["file_name"], {}).get("capture_group", "-")
    rewrite(IMAGE_CSV, img_rows)
    e11.write_class_check(per_class, names, sha, CONF, model_name="final", out_csv=CLASS_CSV)

    # ③ 그래프만 복사 (회사 사진이 들어간 그림은 복사하지 않음) ──────────────────────────
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    copied, missing = [], []
    for src, dst in [("confusion_matrix.png", "final_test_confusion_matrix.png"),
                     ("confusion_matrix_normalized.png", "final_test_confusion_matrix_normalized.png"),
                     ("BoxPR_curve.png", "final_test_pr_curve.png")]:
        if (test_dir / src).exists():
            shutil.copy2(test_dir / src, FIG_DIR / dst)
            copied.append(dst)
        else:
            missing.append(src)

    end = datetime.now()
    log_run({"time": f"{end:%Y-%m-%d %H:%M:%S}", "event": "완료", "weight": "models/final/final_best.pt",
             "weight_sha": sha, "source": info["source"], "imgsz": imgsz, "code": code,
             "reason": f"{(end - start).total_seconds() / 60:.1f}분"})

    # ④ Val(같은 모델) 과 나란히 — 비교만 · 이 숫자로 다시 고르지 않음 ──────────────────────
    v_all = next((r for r in read_csv(REPORTS / f"{info['source']}_metrics.csv") if r["class_id"] == "all"), {})
    v_cls = {r["class_id"]: r for r in read_csv(REPORTS / f"{info['source']}_class_check.csv")}
    t_cls = {r["class_id"]: r for r in read_csv(CLASS_CSV)}
    t_all = rows[0]
    small_gt = sum(int(r["small_gt"]) for r in img_rows)
    small_fn = sum(int(r["small_fn"]) for r in img_rows)
    print(f"\n=== Final Model ({info['source']} · sha {sha}) — Val 74장 vs Frozen Test {n_images}장 ===")
    print(f"  {'지표':<26}{'Val':>10}{'Test':>10}")
    for k, label in [("precision", "P (Ultralytics)"), ("recall", "R (Ultralytics)"), ("map50", "mAP50"), ("map50_95", "mAP50-95")]:
        print(f"  {label:<26}{v_all.get(k, '-'):>10}{t_all[k]:>10}")
    a_v, a_t = v_cls.get("all", {}), t_cls["all"]
    print(f"  {'Recall (conf 0.25)':<26}{a_v.get('recall_at_conf', '-'):>10}{a_t['recall_at_conf']:>10}")
    print(f"  {'GT · FN · FP (conf 0.25)':<26}{a_v.get('gt', '-') + ' · ' + a_v.get('fn', '-') + ' · ' + a_v.get('fp', '-'):>10}"
          f"{a_t['gt'] + ' · ' + a_t['fn'] + ' · ' + a_t['fp']:>16}")
    print(f"  {'작은 객체 FN (Test)':<26}{'':>10}{f'{small_fn} / {small_gt}':>10}")
    print("\n  Class별 Test (conf 0.25)        GT    FN    FP   Recall")
    for cid, r in t_cls.items():
        if cid == "all" or (int(r["gt"]) == 0 and int(r["fp"]) == 0):
            continue
        print(f"    {cid} {r['class_name']:<24}{r['gt']:>4}  {r['fn']:>4}  {r['fp']:>4}   {r['recall_at_conf'] or '-'}")

    print("\n=== 저장 ===")
    for p in [METRICS_CSV, CLASS_CSV, IMAGE_CSV, RUNS_LOG] + [FIG_DIR / c for c in copied]:
        print(f"  OK  {p.relative_to(PROJECT_ROOT)}")
    if missing:
        print(f"  (그림 없음: {missing})")
    print(f"  Git 제외: runs/{RUN_NAME}/ · runs/predict/final_test_images/ (회사 사진)")

    print("\n=== Final 선정 단계 Daily Gate · 산출물 5 ===")
    print("  ✅ reports/final_metrics.csv 에 Frozen Test P · R · mAP50 · mAP50-95 (+ Class별)")
    print(f"  {'✅' if 'final_test_confusion_matrix.png' in copied else '☐'} reports/figures/ 에 Final Test 그래프")
    print("  ✅ 같은 Frozen Test 를 보며 반복 튜닝하지 않음 — final_test_runs.csv 가 증거 · 이제 Final Model 을 바꾸지 않는다")
    print("\n다음: 숫자를 README 14장에 옮겨 적고 커밋 · 낮게 나온 Class 가 있으면 '한계'로 기록 (다시 학습하지 않음)")


if __name__ == "__main__":
    main()
