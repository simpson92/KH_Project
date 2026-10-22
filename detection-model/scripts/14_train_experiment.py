"""개선 실험 단계: 한 변수 개선 실험 학습 (산출물 4).

사용법 (detection-model 폴더에서 · venv 켠 뒤):
    python scripts/14_train_experiment.py --config configs/exp001.yaml --smoke     # ① 1 epoch 시험 (GPU 메모리 · 시간 확인 · 기록 안 남김)
    python scripts/14_train_experiment.py --config configs/exp001.yaml --dry-run   # ② 학습 전 검사만 (몇 초)
    python scripts/14_train_experiment.py --config configs/exp001.yaml             # ③ 본 학습 → 결과 확인 → 기록

※ 요구사항 문서의 이름은 10_train_experiment.py 이지만, 번호는 실행 순서대로 매겼다 (README 6.2 실행표).

입력:
    configs/baseline.yaml · configs/exp001.yaml   두 파일의 학습 설정이 "정확히 하나"만 달라야 학습 시작 (한 변수 원칙)
    reports/improvement_experiment.md             학습 전에 "**상태: 확정**" 으로 작성돼 있어야 함
    configs/dataset.yaml · manifests · data/yolo   Baseline 과 같은 데이터 (09 검증 PASS)

결과:
    runs/exp001/                               Ultralytics 학습 결과 (Git 제외)
    models/improved/exp001_best.pt             best.pt 별도 보관 (산출물 4 · Git 제외)
    reports/exp001_training_condition.md       무엇을 바꿨는지 · 학습 전 검사 · 실행 기록 (Git)
    reports/exp001_results.csv                 runs/exp001/results.csv 사본 (숫자만 · Git)

원칙:
    - 학습 함수는 Baseline 과 같은 src/train_detector.py 를 쓴다 → 차이는 "넘긴 설정 한 줄" 뿐.
    - 평가는 15_evaluate_experiment.py 가 Baseline 과 같은 채점 코드(11)로 한다.
    - Frozen Test 는 쓰지 않는다 (이 스크립트에는 test 평가 코드가 없다).
"""
from pathlib import Path
from datetime import datetime
import argparse
import importlib.util
import shutil
import subprocess
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from src.manifest import read_manifest
from src.train_detector import train_detector, TRAIN_KEYS

# 10 의 도우미(지문 · git · 환경 · results 확인)를 그대로 가져다 쓴다 → 같은 계산 · 코드 중복 없음
_spec = importlib.util.spec_from_file_location("train10", PROJECT_ROOT / "scripts" / "10_train_baseline.py")
t10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(t10)

BASELINE_YAML = PROJECT_ROOT / "configs" / "baseline.yaml"
DATASET_YAML = PROJECT_ROOT / "configs" / "dataset.yaml"
MANIFEST = PROJECT_ROOT / "manifests" / "split_manifest.csv"
LABEL_DIR = PROJECT_ROOT / "data" / "subject7_final" / "labels"
VERIFY_SCRIPT = PROJECT_ROOT / "scripts" / "09_verify_yolo_dataset.py"
PLAN_MD = PROJECT_ROOT / "reports" / "improvement_experiment.md"
RUNS_DIR = PROJECT_ROOT / "runs"
GPU_GB = 12.0                                     # RTX 3060 12GB


def changed_keys(base: dict, exp: dict) -> list[tuple]:
    """학습에 실제로 쓰이는 설정(TRAIN_KEYS + model) 중 Baseline 과 다른 것 목록."""
    keys = [*TRAIN_KEYS, "model"]
    return [(k, base.get(k), exp.get(k)) for k in keys if base.get(k) != exp.get(k)]


def pre_checks(cfg: dict, base: dict, env: dict, mode: str) -> list[dict]:
    checks = []

    def add(item, expected, actual, ok=None, warn_ok=False):
        ok = (str(expected) == str(actual)) if ok is None else ok
        result = "PASS" if ok else ("WARN" if warn_ok else "FAIL")
        checks.append({"item": item, "expected": expected, "actual": actual, "result": result})

    add("Ultralytics 버전 (팀 고정)", cfg["ultralytics_version"], env["ultralytics"])
    add("CUDA (GPU 학습)", True, env["cuda"])
    data_yaml = yaml.safe_load(DATASET_YAML.read_text(encoding="utf-8"))
    yaml_text = " ".join(str(data_yaml.get(k, "")) for k in ("train", "val", "test"))
    add("dataset.yaml Class 수", 7, len(data_yaml.get("names", {})))
    add("dataset.yaml 에 Bridge 없음", "no", "yes" if "bridge" in yaml_text else "no")
    manifest, schema = read_manifest(MANIFEST)
    add("manifest 스키마", "v2", schema)
    add("Dataset Version = Baseline", base["dataset_version"], cfg["dataset_version"])
    add("라벨 지문", cfg["label_fingerprint"], t10.label_fingerprint(LABEL_DIR) if LABEL_DIR.exists() else "라벨 폴더 없음")
    r = subprocess.run([sys.executable, str(VERIFY_SCRIPT)], cwd=PROJECT_ROOT, capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or ["(출력 없음)"])[-1].strip()
    add("09 data/yolo 검증", "종료 코드 0", f"종료 코드 {r.returncode} · {last}", ok=(r.returncode == 0))
    add("시작 가중치 있음", cfg["model"], cfg["model"] if (PROJECT_ROOT / cfg["model"]).exists() else "없음")

    # ★ 한 변수 원칙: 학습 설정이 Baseline 과 정확히 1개만 달라야 함
    diff = changed_keys(base, cfg)
    add("Baseline 과 다른 학습 설정 = 정확히 1개", "1개",
        " · ".join(f"{k} {a} → {b}" for k, a, b in diff) or "없음 (Baseline 과 같음)", ok=(len(diff) == 1))

    if mode != "smoke":
        # 요구사항 §20.3: 학습 전에 계획 문서 확정 (바꿀 변수와 값이 문서에 적혀 있어야 함)
        plan = PLAN_MD.read_text(encoding="utf-8") if PLAN_MD.exists() else ""
        key, _, new = diff[0] if len(diff) == 1 else ("-", None, "-")
        ok = ("**상태: 확정**" in plan) and (f"`{key}`" in plan) and (str(new) in plan)   # 문서 머리의 **상태: 확정** 줄
        add("improvement_experiment.md 확정 · 변수 기록", f"**상태: 확정** · `{key}` · {new}",
            "확정" if ok else ("문서 없음" if not plan else "초안이거나 변수 · 값이 없음"), ok=ok)
        add(f"runs/{cfg['name']} 아직 없음 (덮어쓰기 방지)", "없음", "있음" if (RUNS_DIR / cfg["name"]).exists() else "없음")
        out = PROJECT_ROOT / "models" / "improved" / f"{cfg['name']}_best.pt"
        add(f"models/improved/{out.name} 아직 없음", "없음", "있음" if out.exists() else "없음")

    dirty = t10.git("status", "--porcelain", "--", *t10.TRACKED_FOR_REPRO)
    add("configs · src · scripts · manifests 커밋됨", "변경 없음",
        "변경 없음" if not dirty else f"미커밋 {len(dirty.splitlines())}개", ok=not dirty, warn_ok=(mode != "train"))
    return checks


def write_condition_md(cfg, base, env, checks, state, run=None):
    diff = changed_keys(base, cfg)
    md = PROJECT_ROOT / "reports" / f"{cfg['name']}_training_condition.md"
    L = [f"# {cfg['name']} 학습 조건 (산출물 4)", "",
         f"> **상태**: {state}  ·  **작성**: `scripts/14_train_experiment.py` 자동 생성  ·  **조건 원본**: `configs/{cfg['name']}.yaml`",
         f"> 비교 기준: `{cfg.get('base', 'baseline_v1')}` (`configs/baseline.yaml`) · 계획: `reports/improvement_experiment.md`", "",
         "## 1. 바꾼 것 (한 변수)", "", "| 설정 | Baseline | 이번 실험 |", "|---|---|---|"]
    L += [f"| **{k}** | {a} | **{b}** |" for k, a, b in diff]
    L += ["", f"그 밖의 학습 설정({', '.join(k for k in [*TRAIN_KEYS, 'model'] if k not in [d[0] for d in diff])})은 Baseline 과 같다.",
          f"Dataset Version `{cfg['dataset_version']}` · 라벨 지문 `{cfg['label_fingerprint']}` · Train 600 / Val 74 (Baseline 과 같음)", "",
          f"환경: {env['gpu']} · Ultralytics {env['ultralytics']} · PyTorch {env['torch']} · Python {env['python']} · 코드 `{t10.git('rev-parse', '--short', 'HEAD') or '-'}`",
          "", "## 2. 학습 전 검사", "", "| 결과 | 항목 | 기대 | 실제 |", "|---|---|---|---|"]
    L += [f"| {c['result']} | {c['item']} | {c['expected']} | {c['actual']} |" for c in checks]
    L += ["", "## 3. 실행 기록", ""]
    if run:
        L += ["| 항목 | 값 |", "|---|---|",
              f"| 학습 시작 · 종료 | {run['start']} → {run['end']} ({run['minutes']:.1f}분) |",
              f"| 완료 epoch | {run['rows']} / {cfg['epochs']} |",
              f"| loss NaN · inf | {run['nan_or_inf']}개 |",
              f"| GPU 메모리 최대 (reserved) | {run['gpu_gb']:.2f} GB / {GPU_GB:.0f} GB |",
              f"| 결과 폴더 | `runs/{cfg['name']}/` (Git 제외) |",
              f"| Improved Weight | `models/improved/{cfg['name']}_best.pt` · sha `{run['best_sha']}` (= `runs/{cfg['name']}/weights/best.pt`) |",
              f"| results.csv | 사본 `reports/{cfg['name']}_results.csv` |"]
    else:
        L += ["- (학습 전) 학습을 실행하면 이 칸이 채워진다."]
    L += ["", "> 평가는 `scripts/15_evaluate_experiment.py` (Baseline 과 같은 Val · 같은 채점 코드).", ""]
    md.write_text("\n".join(L), encoding="utf-8")
    return md


def gpu_peak_gb() -> float:
    try:
        import torch
        return torch.cuda.max_memory_reserved() / 1e9 if torch.cuda.is_available() else 0.0
    except ImportError:
        return 0.0


def main():
    parser = argparse.ArgumentParser(description="개선 실험 단계 한 변수 개선 실험 학습")
    parser.add_argument("--config", required=True, help="실험 설정 (예: configs/exp001.yaml)")
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--smoke", action="store_true", help="1 epoch 시험 (GPU 메모리 · 시간) · runs/<name>_smoke · 기록 안 남김")
    g.add_argument("--dry-run", action="store_true", help="학습 전 검사만")
    args = parser.parse_args()
    mode = "smoke" if args.smoke else ("dry" if args.dry_run else "train")

    cfg_path = PROJECT_ROOT / args.config
    if not cfg_path.exists():
        sys.exit(f"[중단] 설정 파일이 없습니다: {args.config}")
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    base = yaml.safe_load(BASELINE_YAML.read_text(encoding="utf-8"))
    cfg["ultralytics_version"] = str(cfg["ultralytics_version"])
    if cfg.get("name") in (None, base.get("name")):
        sys.exit("[중단] 실험 이름(name)이 없거나 Baseline 과 같습니다")

    env = t10.environment()
    checks = pre_checks(cfg, base, env, mode)
    print(f"=== 학습 전 검사 ({mode}) ===")
    for c in checks:
        print(f"  {c['result']}  {c['item']:<38} 기대 {c['expected']} / 실제 {c['actual']}")
    n_fail = sum(c["result"] == "FAIL" for c in checks)
    print(f"  → PASS {sum(c['result'] == 'PASS' for c in checks)} / WARN {sum(c['result'] == 'WARN' for c in checks)} / FAIL {n_fail}")
    if n_fail:
        sys.exit("\n[중단] FAIL 이 있어 학습하지 않았습니다.")
    if mode == "dry":
        write_condition_md(cfg, base, env, checks, "학습 전 (dry-run)")
        print(f"\n--dry-run: 검사만 했습니다 · reports/{cfg['name']}_training_condition.md (초안)")
        return

    # ── ① Smoke: 1 epoch 로 메모리 · 시간만 본다 (본 학습 폴더 · 모델 · 기록에는 손대지 않음) ─────────
    if mode == "smoke":
        name = f"{cfg['name']}_smoke"
        smoke_dir = RUNS_DIR / name
        if smoke_dir.exists():
            assert smoke_dir.resolve().parent == RUNS_DIR.resolve()       # 지우는 대상이 runs/ 바로 아래인지 한 번 더
            shutil.rmtree(smoke_dir)
        s_cfg = {**cfg, "epochs": 1, "patience": 1}
        print(f"\n=== Smoke: 1 epoch · imgsz {cfg['imgsz']} · batch {cfg['batch']} → runs/{name} ===")
        t0 = time.time()
        try:
            train_detector(str(PROJECT_ROOT / cfg["model"]), str(DATASET_YAML), s_cfg, RUNS_DIR, name)
        except RuntimeError as e:                                     # CUDA out of memory 등
            if "out of memory" in str(e).lower():
                sys.exit(f"\n[OOM] GPU 메모리 부족 · imgsz {cfg['imgsz']} · batch {cfg['batch']} → 회의에서 imgsz 960 또는 batch 조정 결정 (batch 를 바꾸면 변수 2개 · 기록)")
            raise
        sec, gb = time.time() - t0, gpu_peak_gb()
        print("\n=== Smoke 결과 (기록용 아님 · 판단용) ===")
        print(f"  1 epoch 시간      {sec / 60:.1f}분 (학습 + Val 1회 · 첫 epoch 은 준비 시간이 섞여 조금 김)")
        print(f"  50 epoch 예상     약 {sec * cfg['epochs'] / 60:.0f}분 (위 시간 × {cfg['epochs']} · 실제는 이보다 조금 짧은 경우가 많음)")
        print(f"  GPU 메모리 최대   {gb:.2f} GB / {GPU_GB:.0f} GB" + ("  ⚠ 여유 1GB 미만 → 본 학습 중 OOM 위험" if gb > GPU_GB - 1 else "  ✓ 여유 있음"))
        print("  Baseline 참고    640 · batch 16 → 1 epoch 약 0.3분 · 50 epoch 13.9분 · GPU_mem 2.48G")
        print(f"\n다음: reports/improvement_experiment.md 머리의 '초안' 을 '확정' 으로 바꾼 뒤 → python scripts/14_train_experiment.py --config {args.config}")
        return

    # ── ② 본 학습 ───────────────────────────────────────────────────────────
    write_condition_md(cfg, base, env, checks, "학습 전")
    start = datetime.now()
    print(f"\n=== 학습 시작 {start:%Y-%m-%d %H:%M:%S} · {cfg['epochs']} epoch · runs/{cfg['name']} ===")
    save_dir = train_detector(str(PROJECT_ROOT / cfg["model"]), str(DATASET_YAML), cfg, RUNS_DIR, cfg["name"])
    end, gb = datetime.now(), gpu_peak_gb()

    problems = []
    if save_dir.name != cfg["name"]:
        problems.append(f"결과 폴더 이름이 {save_dir.name} (기대 {cfg['name']})")
    results_csv, best = save_dir / "results.csv", save_dir / "weights" / "best.pt"
    for p in (results_csv, best, save_dir / "weights" / "last.pt"):
        if not p.exists():
            problems.append(f"없음: {p.relative_to(PROJECT_ROOT)}")
    if problems:
        sys.exit("[FAIL] " + " · ".join(problems))
    res = t10.check_results(results_csv, cfg["epochs"])
    if res["nan_or_inf"]:
        problems.append(f"loss 에 NaN/inf {res['nan_or_inf']}개")
    if res["rows"] < cfg["epochs"] and cfg["patience"] >= cfg["epochs"]:
        problems.append(f"완료 epoch {res['rows']} < {cfg['epochs']}")

    out = PROJECT_ROOT / "models" / "improved" / f"{cfg['name']}_best.pt"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, out)
    shutil.copy2(results_csv, PROJECT_ROOT / "reports" / f"{cfg['name']}_results.csv")
    run = {"start": f"{start:%Y-%m-%d %H:%M}", "end": f"{end:%Y-%m-%d %H:%M}", "gpu_gb": gb,
           "minutes": (end - start).total_seconds() / 60, "best_sha": t10.sha12(out), **res}
    md = write_condition_md(cfg, base, env, checks, "완료" if not problems else "확인 필요", run)

    print(f"\n=== {cfg['name']} 학습 결과 ===")
    print(f"  완료 epoch {res['rows']} / {cfg['epochs']} · NaN/inf {res['nan_or_inf']} · {run['minutes']:.1f}분 · GPU 최대 {gb:.2f} GB")
    print(f"  보관: models/improved/{out.name} (sha {run['best_sha']}) · reports/{cfg['name']}_results.csv")
    print(f"  기록: {md.relative_to(PROJECT_ROOT)}")
    if problems:
        print("\n[확인 필요] " + " · ".join(problems))
        sys.exit(1)
    print(f"\n다음: python scripts/15_evaluate_experiment.py --config {args.config}   (같은 Val · 같은 채점 코드)")


if __name__ == "__main__":
    main()
