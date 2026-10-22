"""Baseline 학습 단계: 팀 공통 Baseline 학습 (산출물 2).

사용법 (detection-model 폴더에서 실행):
    python scripts/10_train_baseline.py --dry-run    # ① 학습 전 검사만 + 조건 문서 미리 쓰기 (학습 안 함 · 몇 초)
    python scripts/10_train_baseline.py              # ② 검사 → 학습(약 40분) → 결과 확인 → 기록

※ 요구사항 문서의 이름은 scripts/06_train_baseline.py 이지만, 번호는 실행 순서대로 매겼다 (README 6.2 실행표).

입력:
    configs/baseline.yaml       학습 조건 (팀 확정값 · 이 스크립트는 숫자를 따로 갖지 않음)
    configs/dataset.yaml        train · val (test 는 학습에 쓰이지 않음 · Bridge 없음)
    manifests/split_manifest.csv · data/yolo (09 검증 PASS 여야 함)

결과 (Gate):
    runs/baseline_v1/                         results.csv · weights/best.pt · last.pt · 그래프   (Git 제외)
    models/baseline/baseline_best.pt          best.pt 별도 보관 (산출물 2)                      (Git 제외)
    reports/baseline_training_condition.md    실제 학습 조건 · 실행 기록 · Gate 확인 (산출물 2)    (Git 올림)
    reports/baseline_results.csv              runs/baseline_v1/results.csv 사본 (숫자만)          (Git 올림)

원칙:
    - 학습 전 검사(버전 · 데이터 · 지문 · 09 · 덮어쓰기 · GPU · 커밋 상태)를 모두 통과해야 학습을 시작한다.
    - 성능 해석은 Baseline 평가 단계. 오늘은 "끝까지 학습됐는가 · NaN 이 없는가 · 파일이 남았는가"만 확인한다.
    - Frozen Test 로 평가하지 않는다 (이 스크립트에는 test 평가 코드가 없다).
"""
from pathlib import Path
from datetime import datetime
import argparse
import csv
import hashlib
import math
import platform
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from src.manifest import read_manifest, fingerprint
from src.train_detector import train_detector, TRAIN_KEYS

# ----------------------------------------------------------------------
# 경로
# ----------------------------------------------------------------------
BASELINE_YAML = PROJECT_ROOT / "configs" / "baseline.yaml"
DATASET_YAML = PROJECT_ROOT / "configs" / "dataset.yaml"
MANIFEST_DIR = PROJECT_ROOT / "manifests"
LABEL_DIR = PROJECT_ROOT / "data" / "subject7_final" / "labels"
VERIFY_SCRIPT = PROJECT_ROOT / "scripts" / "09_verify_yolo_dataset.py"
RUNS_DIR = PROJECT_ROOT / "runs"                                   # 절대경로 (project 로 넘김)
MODEL_OUT = PROJECT_ROOT / "models" / "baseline" / "baseline_best.pt"
CONDITION_MD = PROJECT_ROOT / "reports" / "baseline_training_condition.md"
RESULTS_COPY = PROJECT_ROOT / "reports" / "baseline_results.csv"
TRACKED_FOR_REPRO = ["configs", "src", "scripts", "manifests"]     # 학습 조건에 영향 → 커밋된 상태여야 함

FROZEN_TEST_FP = "4f9291849fe6"                                    # split_policy.md 8장 (학습에 안 쓰는지 기록용)
REQUIRED_KEYS = ["name", "dataset_version", "label_fingerprint", "ultralytics_version", "model", *TRAIN_KEYS]


def sha12(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def label_fingerprint(label_dir: Path) -> str:
    """README 6.1 `LC_ALL=C cat labels/*.txt | sha256sum` 과 같은 값 (06 과 같은 계산)."""
    h = hashlib.sha256()
    for p in sorted(label_dir.glob("*.txt"), key=lambda p: p.name.encode("utf-8")):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def git(*args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def environment() -> dict:
    """학습 환경 기록 (GPU · Ultralytics Version)."""
    env = {"python": platform.python_version(), "torch": "-", "cuda": False, "gpu": "-", "ultralytics": "-"}
    try:
        import torch
        env["torch"] = torch.__version__
        env["cuda"] = bool(torch.cuda.is_available())
        if env["cuda"]:
            env["gpu"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    try:
        import ultralytics
        env["ultralytics"] = ultralytics.__version__
    except ImportError:
        pass
    return env


def pre_checks(cfg: dict, env: dict, dry_run: bool) -> tuple[list[dict], dict]:
    """학습 전 검사. (검사 목록, 기록용 정보) 를 돌려준다."""
    checks, info = [], {}

    def add(item, expected, actual, ok=None):
        ok = (str(expected) == str(actual)) if ok is None else ok
        checks.append({"item": item, "expected": expected, "actual": actual, "result": "PASS" if ok else "FAIL"})

    # ① 환경
    add("Ultralytics 버전 (팀 고정)", cfg["ultralytics_version"], env["ultralytics"])
    add("CUDA (GPU 학습)", True, env["cuda"])

    # ② 데이터 · 설정
    data_yaml = yaml.safe_load(DATASET_YAML.read_text(encoding="utf-8"))
    yaml_text = " ".join(str(data_yaml.get(k, "")) for k in ("train", "val", "test"))
    add("dataset.yaml Class 수", 7, len(data_yaml.get("names", {})))
    add("dataset.yaml 에 Bridge 없음", "no", "yes" if "bridge" in yaml_text else "no")

    manifest, schema = read_manifest(MANIFEST_DIR / "split_manifest.csv")
    versions = ",".join(sorted({r.get("dataset_version", "-") for r in manifest}))
    add("manifest 스키마", "v2", schema)
    add("Dataset Version", cfg["dataset_version"], versions)
    add("라벨 지문", cfg["label_fingerprint"], label_fingerprint(LABEL_DIR) if LABEL_DIR.exists() else "라벨 폴더 없음")
    info["train_n"] = sum(r["split"] == "train" for r in manifest)
    info["val_n"] = sum(r["split"] == "val" for r in manifest)
    info["test_fp"] = fingerprint(r["file_name"] for r in manifest if r["split"] == "test")
    info["train_csv"] = sha12(MANIFEST_DIR / "train.csv")
    info["val_csv"] = sha12(MANIFEST_DIR / "val.csv")

    # ③ data/yolo = manifest (09 검증을 그대로 실행 · 종료 코드 0 이어야 함)
    r = subprocess.run([sys.executable, str(VERIFY_SCRIPT)], cwd=PROJECT_ROOT, capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or ["(출력 없음)"])[-1].strip()
    add("09 data/yolo 검증", "종료 코드 0", f"종료 코드 {r.returncode} · {last}", ok=(r.returncode == 0))

    # ④ 시작 가중치 · 덮어쓰기 방지
    model_path = PROJECT_ROOT / cfg["model"]
    add("시작 가중치 있음", cfg["model"], cfg["model"] if model_path.exists() else "없음")
    run_dir = RUNS_DIR / cfg["name"]
    add(f"runs/{cfg['name']} 아직 없음 (덮어쓰기 방지)", "없음", "있음" if run_dir.exists() else "없음")
    add("models/baseline/baseline_best.pt 아직 없음", "없음", "있음" if MODEL_OUT.exists() else "없음")

    # ⑤ 재현성: 학습에 영향 주는 파일이 커밋된 상태인가 (dry-run 은 경고만)
    dirty = git("status", "--porcelain", "--", *TRACKED_FOR_REPRO)
    info["commit"] = git("rev-parse", "--short", "HEAD") or "-"
    add("configs · src · scripts · manifests 커밋됨", "변경 없음", "변경 없음" if not dirty else f"미커밋 {len(dirty.splitlines())}개",
        ok=(not dirty) or dry_run)
    if dirty and dry_run:
        checks[-1]["result"] = "WARN"            # dry-run 은 경고만 · 실제 학습 전에는 커밋해야 통과
    return checks, info


def check_results(results_csv: Path, epochs: int) -> dict:
    """results.csv 확인: 몇 epoch 끝났나 · loss 에 NaN/inf 가 있나."""
    with open(results_csv, encoding="utf-8", newline="") as f:
        rows = [{k.strip(): v.strip() for k, v in r.items()} for r in csv.DictReader(f)]
    loss_cols = [k for k in (rows[0] if rows else {}) if "loss" in k]
    bad = 0
    for r in rows:
        for k in loss_cols:
            try:
                v = float(r[k])
                bad += (math.isnan(v) or math.isinf(v))
            except ValueError:
                bad += 1
    return {"rows": len(rows), "epochs": epochs, "loss_cols": len(loss_cols), "nan_or_inf": bad}


def write_condition_md(cfg, env, checks, info, state, run=None):
    """reports/baseline_training_condition.md (반드시 기록할 항목 + 실행 기록 + Gate)."""
    ck = "✅" if state == "완료" else "☐"
    L = [
        "# Baseline 학습 조건 (산출물 2)",
        "",
        f"> **상태**: {state}  ·  **작성**: `scripts/10_train_baseline.py` 자동 생성  ·  **조건 원본**: `configs/baseline.yaml`",
        "> 성능 해석은 Baseline 평가 단계 `reports/baseline_metrics.csv` 에서 한다. 이 문서는 '어떤 조건으로 학습했는가'만 기록한다.",
        "",
        "## 1. 학습 조건 (Freeze)",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| Model | YOLO11n (`{cfg['model']}` · pretrained={cfg['pretrained']}) |",
        f"| Dataset Version | `{cfg['dataset_version']}` · 라벨 지문 `{cfg['label_fingerprint']}` |",
        f"| Train / Val Manifest | 스키마 v2 · Train {info.get('train_n', '-')}장 (`train.csv` sha `{info.get('train_csv', '-')}`) · "
        f"Val {info.get('val_n', '-')}장 (`val.csv` sha `{info.get('val_csv', '-')}`) |",
        f"| Epoch · Patience | {cfg['epochs']} · {cfg['patience']} |",
        f"| Batch | {cfg['batch']} |",
        f"| Image Size | {cfg['imgsz']} |",
        f"| Seed · Deterministic | {cfg['seed']} · {cfg['deterministic']} |",
        f"| Optimizer · Learning Rate · Momentum | {cfg['optimizer']} · {cfg['lr0']} · {cfg['momentum']} (auto 대신 명시 고정) |",
        f"| AMP · Workers | {cfg['amp']} · {cfg['workers']} |",
        f"| GPU | {env['gpu']} (CUDA {env['cuda']}) |",
        f"| Ultralytics · PyTorch · Python | {env['ultralytics']} · {env['torch']} · {env['python']} |",
        f"| 코드 버전 (git commit) | `{info.get('commit', '-')}` |",
        "",
        "## 2. 학습 전 검사",
        "",
        "| 결과 | 항목 | 기대 | 실제 |",
        "|---|---|---|---|",
    ]
    L += [f"| {c['result']} | {c['item']} | {c['expected']} | {c['actual']} |" for c in checks]
    L += ["", "## 3. 실행 기록", ""]
    if run:
        L += ["| 항목 | 값 |", "|---|---|",
              f"| 학습 시작 · 종료 | {run['start']} → {run['end']} ({run['minutes']:.1f}분) |",
              f"| 완료 epoch | {run['rows']} / {cfg['epochs']} |",
              f"| loss NaN · inf | {run['nan_or_inf']}개 ({run['loss_cols']}개 loss 칸 검사) |",
              f"| 결과 폴더 | `runs/{cfg['name']}/` (Git 제외) |",
              f"| Baseline Weight | `models/baseline/baseline_best.pt` · sha `{run['best_sha']}` (= `runs/{cfg['name']}/weights/best.pt`) |",
              f"| results.csv | `runs/{cfg['name']}/results.csv` · 사본 `reports/baseline_results.csv` |"]
    else:
        L += ["- (학습 전 · `--dry-run` 결과) 학습을 실행하면 이 칸이 채워진다."]
    L += ["", "## 4. Baseline 학습 단계 Daily Gate", "",
          f"- {ck} 전체 Train Dataset({info.get('train_n', '-')}장)으로 Baseline 학습이 완료되었습니다.",
          f"- {'✅' if checks else '☐'} `reports/baseline_training_condition.md`에 실제 학습조건을 기록했습니다. (이 문서)",
          f"- {ck} `models/baseline/baseline_best.pt`가 별도 보관되었습니다.",
          f"- {ck} `runs/{cfg['name']}/results.csv`를 보존했습니다. (사본 `reports/baseline_results.csv`)",
          f"- ✅ Dataset Version을 확인할 수 있습니다. (`{cfg['dataset_version']}` · 라벨 지문 · manifest sha)",
          f"- {ck} Frozen Test와 Bridge Holdout을 사용하지 않았습니다. (dataset.yaml 에 Bridge 없음 · test 평가 코드 없음 · "
          f"Test 지문 `{info.get('test_fp', '-')}` 기록만)",
          "", "> `reports/baseline_metrics.csv`는 Validation 평가 후 작성합니다.", ""]
    CONDITION_MD.parent.mkdir(exist_ok=True)
    CONDITION_MD.write_text("\n".join(L), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Baseline 학습 단계 팀 공통 Baseline 학습")
    parser.add_argument("--dry-run", action="store_true", help="학습 전 검사 + 조건 문서만 (학습 안 함)")
    args = parser.parse_args()

    if not BASELINE_YAML.exists():
        sys.exit(f"[중단] 학습 조건 파일이 없습니다: {BASELINE_YAML.relative_to(PROJECT_ROOT)}")
    cfg = yaml.safe_load(BASELINE_YAML.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_KEYS if k not in cfg]
    if missing:
        sys.exit(f"[중단] configs/baseline.yaml 에 없는 항목: {missing}")
    cfg["ultralytics_version"] = str(cfg["ultralytics_version"])

    env = environment()
    checks, info = pre_checks(cfg, env, args.dry_run)

    print("=== 학습 전 검사 ===")
    for c in checks:
        print(f"  {c['result']}  {c['item']:<36} 기대 {c['expected']} / 실제 {c['actual']}")
    n_fail = sum(c["result"] == "FAIL" for c in checks)
    print(f"  → PASS {len(checks) - n_fail} / FAIL {n_fail}")

    state = "학습 전 (dry-run)" if args.dry_run else "학습 전"
    write_condition_md(cfg, env, checks, info, state)
    print(f"  조건 문서: {CONDITION_MD.relative_to(PROJECT_ROOT)} ({state})")
    if n_fail:
        sys.exit("\n[중단] FAIL 이 있어 학습을 시작하지 않았습니다.")
    if args.dry_run:
        print("\n--dry-run: 검사만 했습니다. 조건 문서를 팀과 확인한 뒤 --dry-run 없이 실행하세요.")
        return

    # ── 학습 ────────────────────────────────────────────────────────────────
    start = datetime.now()
    print(f"\n=== 학습 시작 {start:%Y-%m-%d %H:%M:%S} · {cfg['epochs']} epoch · runs/{cfg['name']} ===")
    save_dir = train_detector(str(PROJECT_ROOT / cfg["model"]), str(DATASET_YAML), cfg, RUNS_DIR, cfg["name"])
    end = datetime.now()

    # ── 학습 후 확인 · 보관 ──────────────────────────────────────────────────
    problems = []
    if save_dir.name != cfg["name"]:
        problems.append(f"결과 폴더 이름이 {save_dir.name} (기대 {cfg['name']})")
    results_csv, best, last = save_dir / "results.csv", save_dir / "weights" / "best.pt", save_dir / "weights" / "last.pt"
    for p in (results_csv, best, last):
        if not p.exists():
            problems.append(f"없음: {p.relative_to(PROJECT_ROOT)}")
    if problems:
        sys.exit("[FAIL] " + " · ".join(problems))

    res = check_results(results_csv, cfg["epochs"])
    if res["nan_or_inf"]:
        problems.append(f"loss 에 NaN/inf {res['nan_or_inf']}개")
    if res["rows"] < cfg["epochs"] and cfg["patience"] >= cfg["epochs"]:
        problems.append(f"완료 epoch {res['rows']} < {cfg['epochs']} (조기 종료 설정이 아닌데 덜 끝남)")

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, MODEL_OUT)                                   # 산출물 2: best.pt 별도 보관
    shutil.copy2(results_csv, RESULTS_COPY)                         # 숫자만 → Git 에 남길 사본
    run = {"start": f"{start:%Y-%m-%d %H:%M}", "end": f"{end:%Y-%m-%d %H:%M}",
           "minutes": (end - start).total_seconds() / 60, "best_sha": sha12(MODEL_OUT), **res}

    write_condition_md(cfg, env, checks, info, "완료" if not problems else "확인 필요", run)
    print("\n=== Baseline 학습 결과 ===")
    print(f"  완료 epoch {res['rows']} / {cfg['epochs']} · loss NaN/inf {res['nan_or_inf']}개 · {run['minutes']:.1f}분")
    print(f"  보관: models/baseline/baseline_best.pt (sha {run['best_sha']}) · reports/baseline_results.csv")
    print(f"  기록: {CONDITION_MD.relative_to(PROJECT_ROOT)}")
    if problems:
        print("\n[확인 필요] " + " · ".join(problems))
        sys.exit(1)
    print("\nGate: 학습 완료 · 조건 기록 · Weight 보관 · results.csv 보존 · Dataset Version · Test/Bridge 미사용 → 모두 충족")


if __name__ == "__main__":
    main()
