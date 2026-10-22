"""Final 선정 단계: Final Model 로 Detection 이미지 + Auto Label 후보 만들기 → 라벨 검수 도구 검수 준비 (21.4 · 산출물 6).

사용법 (detection-model 폴더에서 · venv 켠 뒤 · Frozen Test 평가(16)가 끝난 뒤):
    python scripts/17_auto_label.py --dry-run     # ① 검사 + 어떤 사진을 쓸지만 보여 줌 (아무것도 만들지 않음)
    python scripts/17_auto_label.py               # ② Test 사진 8장으로 Detection · 후보 TXT · 검수용 폴더 만들기
    python scripts/17_auto_label.py --n 6         #    장수 바꾸기 (요구사항 권장 5~10)

※ 요구사항 문서의 이름은 12_auto_label.py 이지만, 번호는 실행 순서대로 매겼다 (README 6.2 실행표).

왜 Test 사진인가:
    새 사진(학습 · Val · Test 에 안 쓴 사진)이 없으면, Frozen Test 최종평가를 "모두 끝낸 뒤" Test 사진 5~10장을 복사하고
    정답 TXT 는 따로 보관한 채 Auto Label 흐름만 시연할 수 있다. 이 결과로 모델을 다시 학습하거나 Test 성능을 맞추지 않는다.
    → 이 스크립트는 reports/final_metrics.csv (16 의 결과)가 있어야만 실행된다. Bridge Holdout 사진은 거부한다.

결과 (전부 Git 제외 · 회사 사진 · 라벨):
    demo/prediction_images/*.jpg                          Final Model Detection 결과 (BBox · Class · Confidence 표시) — 시연 1
    demo/auto_label/candidate_labels/*.txt                AI 가 만든 YOLO 후보 라벨 (class x y w h · 확신도 없음 · save_conf=False 와 같음)
    demo/auto_label/review_workspace/                     라벨 검수 도구으로 "data 폴더 열기" 할 폴더 — 시연 2
        raw/auto_label/images/test/*.jpg                  검수할 사진 (복사본)
        raw/auto_label/labels/test/*.txt                  = 후보 TXT (프로그램이 '원본 라벨'로 불러옴 · 사람이 고치면 work/ 에 저장)
    demo/auto_label/gt_hidden/*.txt                       Test 정답 TXT (검수자에게 보여 주지 않음 · 18 이 비교에만 사용)
결과 (Git · 숫자만):
    reports/auto_label_candidates.csv                     사진별 후보 BBox 수 · Class · 정답 수(비교용)
"""
from pathlib import Path
from datetime import datetime
import argparse
import csv
import importlib.util
import re
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from src.manifest import read_manifest
from src.evaluate_detector import predict_images


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / "scripts" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


f16 = _load("final16", "16_evaluate_final_test.py")     # 선택 문서 읽기 · sha · Final 경로 (같은 규칙)

REPORTS = PROJECT_ROOT / "reports"
DEMO = PROJECT_ROOT / "demo"
AUTO = DEMO / "auto_label"
CAND_DIR = AUTO / "candidate_labels"
GT_DIR = AUTO / "gt_hidden"
WS = AUTO / "review_workspace"                        # 라벨 검수 도구이 여는 data 폴더
WS_IMAGES = WS / "raw" / "auto_label" / "images" / "test"
WS_LABELS = WS / "raw" / "auto_label" / "labels" / "test"
PRED_DIR_NAME = "prediction_images"                   # demo/prediction_images
CAND_CSV = REPORTS / "auto_label_candidates.csv"
MANIFESTS = PROJECT_ROOT / "manifests"
CONF = 0.25
N_DEFAULT = 8
CLASS_IDS = [0, 1, 2, 3, 5, 6]                        # 4(고무장갑)는 미사용


def read_yolo(path: Path) -> list[tuple]:
    out = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            p = line.split()
            if len(p) == 5:
                out.append((int(p[0]), *map(float, p[1:])))
    return out


def choose_images(test_rows: list[dict], n: int) -> list[str]:
    """Class 를 골고루 · 촬영 세션도 골고루 · 박스가 너무 많지 않은 사진 (같은 입력이면 늘 같은 결과).
    한 장씩 고를 때: ① 아직 안 나온 Class 수 ② 아직 안 쓴 세션 ③ Class 종류 수 ④ 박스 수 적은 순 ⑤ 파일명"""
    info = {}
    for r in test_rows:
        gts = read_yolo(f16.TEST_LABELS / (Path(r["file_name"]).stem + ".txt"))
        info[r["file_name"]] = (set(g[0] for g in gts), len(gts), r.get("capture_group", "-"))
    chosen, covered, groups = [], set(), set()
    while len(chosen) < min(n, len(info)):
        best = min((k for k in info if k not in chosen),
                   key=lambda k: (-len(info[k][0] - covered), info[k][2] in groups, -len(info[k][0]), info[k][1], k))
        chosen.append(best)
        covered |= info[best][0]
        groups.add(info[best][2])
    return chosen


def pre_checks(info: dict, chosen: list[str], cfg: dict, force_new: bool) -> list[dict]:
    checks = []

    def add(item, expected, actual, ok=None):
        ok = (str(expected) == str(actual)) if ok is None else ok
        checks.append({"item": item, "expected": expected, "actual": actual, "result": "PASS" if ok else "FAIL"})

    add("final_model_selection.md 확정", "**상태: 확정**", "**상태: 확정**" if info["confirmed"] else "아님")
    add("models/final/final_best.pt 있음", "있음", "있음" if f16.FINAL_PT.exists() else "없음")
    sha = f16.e11.sha12(f16.FINAL_PT) if f16.FINAL_PT.exists() else "-"
    add("Final sha = 선택 문서", info["final_sha"], sha)
    add("Frozen Test 평가 끝남 (Test 사진은 그 뒤에만)", "final_metrics.csv 있음",
        "final_metrics.csv 있음" if f16.METRICS_CSV.exists() else "없음 → 16 먼저", ok=f16.METRICS_CSV.exists())
    add("imgsz = Final 원본 설정", f"{info['config']} 의 imgsz", cfg.get("imgsz", "-"), ok=bool(cfg.get("imgsz")))

    split_of = {}
    for name in ("train", "val", "test", "bridge_holdout"):
        for r in read_manifest(MANIFESTS / f"{name}.csv")[0]:
            split_of[r["file_name"]] = name
    bad = [c for c in chosen if split_of.get(c) != "test"]
    add(f"고른 사진 {len(chosen)}장 = 전부 Frozen Test (Bridge · Train · Val 아님)", "전부 test",
        "전부 test" if not bad else f"아님 {bad[:3]}", ok=not bad and bool(chosen))
    missing = [c for c in chosen if not (f16.TEST_IMAGES / c).exists()]
    add("사진 파일 있음 (data/yolo/images/test)", "전부 있음", "전부 있음" if not missing else f"없음 {missing[:3]}", ok=not missing)

    started = any((WS / s / "labels").glob("*.txt") for s in ("work", "final")) if WS.exists() else False
    add("사람 검수 아직 시작 전 (덮어쓰기 방지)", "시작 전",
        "시작 전" if not started else ("검수 기록 있음 · --force-new 로 새로 만듦" if force_new else "검수 기록 있음 (review_workspace/work · final)"),
        ok=(not started) or force_new)
    return checks


def main():
    parser = argparse.ArgumentParser(description="Detection · Auto Label 후보 (Test 사진 시연)")
    parser.add_argument("--n", type=int, default=N_DEFAULT, help="사진 장수 (요구사항 5~10장 · 기본 8)")
    parser.add_argument("--dry-run", action="store_true", help="검사 + 사진 목록만")
    parser.add_argument("--force-new", action="store_true", help="이미 사람 검수를 시작한 폴더를 지우고 새로 만들기 (팀 확인 후에만)")
    args = parser.parse_args()
    if not 1 <= args.n <= 10:
        sys.exit("[중단] --n 은 1~10 (은 5~10장)")

    info = f16.selection_info()
    cfg_path = PROJECT_ROOT / info["config"]
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.is_file() else {}
    test_rows = read_manifest(MANIFESTS / "test.csv")[0]
    chosen = choose_images(test_rows, args.n)
    checks = pre_checks(info, chosen, cfg, args.force_new)

    print(f"=== Auto Label 준비 검사 ({'dry-run' if args.dry_run else 'run'}) ===")
    for c in checks:
        print(f"  {c['result']}  {c['item']:<52} 기대 {c['expected']} / 실제 {c['actual']}")
    n_fail = sum(c["result"] == "FAIL" for c in checks)
    print(f"  → PASS {len(checks) - n_fail} / FAIL {n_fail}")

    group = {r["file_name"]: r.get("capture_group", "-") for r in test_rows}
    print(f"\n=== 고른 Test 사진 {len(chosen)}장 (Class · 세션 골고루 · 같은 입력이면 늘 같은 목록) ===")
    for c in chosen:
        gts = read_yolo(f16.TEST_LABELS / (Path(c).stem + ".txt"))
        print(f"  {c}   세션 {group.get(c, '-'):<7} 정답 {len(gts):>2}개 · Class {sorted(set(g[0] for g in gts))}")
    if n_fail:
        sys.exit("\n[중단] FAIL 이 있어 만들지 않았습니다.")
    if args.dry_run:
        print("\n--dry-run: 아무것도 만들지 않았습니다. 다음: python scripts/17_auto_label.py")
        return

    # ── ① 폴더 준비 (demo/ 는 Git 제외) ──────────────────────────────────────────────
    for d in (WS, CAND_DIR, GT_DIR, DEMO / PRED_DIR_NAME):
        if d.exists():
            assert d.resolve().is_relative_to(DEMO.resolve())             # demo/ 밖은 절대 지우지 않음
            shutil.rmtree(d)
    for d in (WS_IMAGES, WS_LABELS, CAND_DIR, GT_DIR):
        d.mkdir(parents=True, exist_ok=True)
    for c in chosen:
        shutil.copy2(f16.TEST_IMAGES / c, WS_IMAGES / c)                   # 검수할 사진 (복사본)
        shutil.copy2(f16.TEST_LABELS / (Path(c).stem + ".txt"), GT_DIR / (Path(c).stem + ".txt"))   # 정답은 따로

    # ── ② Final Model 예측 → Detection 이미지 + 후보 TXT ─────────────────────────────────
    imgsz = int(cfg["imgsz"])
    print(f"\n=== Final Model 예측 (conf {CONF} · imgsz {imgsz}) → demo/{PRED_DIR_NAME}/ · 후보 TXT ===")
    rows = []
    for name, size, preds in predict_images(str(f16.FINAL_PT), WS_IMAGES, CONF, imgsz, DEMO, PRED_DIR_NAME):
        lines = [f"{p[0]} {p[2]:.6f} {p[3]:.6f} {p[4]:.6f} {p[5]:.6f}" for p in preds]   # 확신도는 저장하지 않음
        text = "\n".join(lines) + ("\n" if lines else "")
        stem = Path(name).stem
        (CAND_DIR / f"{stem}.txt").write_text(text, encoding="utf-8")
        (WS_LABELS / f"{stem}.txt").write_text(text, encoding="utf-8")   # 라벨 검수 도구이 '원본 라벨'로 불러올 파일
        gts = read_yolo(GT_DIR / f"{stem}.txt")
        rows.append({"image": name, "capture_group": group.get(name, "-"), "candidate_boxes": len(preds),
                     "candidate_classes": " ".join(str(c) for c in sorted(set(p[0] for p in preds))) or "-",
                     "min_conf": f"{min((p[1] for p in preds), default=0):.3f}",
                     "gt_boxes_hidden": len(gts), "source_split": "test",
                     "made_at": f"{datetime.now():%Y-%m-%d %H:%M}"})
        print(f"  ✓ {name}   후보 {len(preds):>2}개 (정답 {len(gts)}개 · 검수자에게는 비공개)")

    with open(CAND_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    total = sum(r["candidate_boxes"] for r in rows)
    print(f"\n=== 저장 ===")
    print(f"  demo/{PRED_DIR_NAME}/              Detection 결과 {len(rows)}장 (BBox · Class · Confidence)  [Git 제외]")
    print(f"  demo/auto_label/candidate_labels/  후보 TXT {len(rows)}개 · BBox {total}개              [Git 제외]")
    print(f"  demo/auto_label/review_workspace/  라벨 검수 도구 검수용 폴더                       [Git 제외]")
    print(f"  demo/auto_label/gt_hidden/         정답 TXT (검수자에게 보여 주지 않음)              [Git 제외]")
    print(f"  {CAND_CSV.relative_to(PROJECT_ROOT)}   사진별 후보 수 (숫자만)                          [Git]")
    print(f"""
=== 다음: 사람 검수 (라벨 검수 도구 v4.1) ===
  1) 최상위에서:  cd ../labeling-qa-tool && python main.py
  2) 파일 > data 폴더 열기 (Ctrl+O) → detection-model/demo/auto_label/review_workspace 선택  (목록 {len(rows)}장 · 박스 = AI 후보)
  3) 작업자로 로그인 → 사진마다 박스 확인 · Class 수정 · 박스 수정 · 삭제 · 놓친 이물 추가 · scene_type 선택
     - 고칠 것이 없으면 그대로 저장 → status DONE (= 그대로 승인)
     - 하나라도 고치면 저장 → status EDITED · 판단이 어려우면 REVIEW + 사유
     - 저장 위치: review_workspace/work/labels/  (후보 TXT 는 그대로 남음)
  4) (선택) 다른 팀원이 검수자로 QA PASS → review_workspace/final/
  5) 끝나면: python scripts/18_auto_label_review.py  → 승인 · 수정 · 삭제 · 추가 집계
  ※ gt_hidden/ 의 정답은 검수 중에 열지 않습니다 (사람 검수를 정답에 맞추지 않기 위해).""")


if __name__ == "__main__":
    main()
