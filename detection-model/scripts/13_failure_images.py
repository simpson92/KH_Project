"""실패 분석 단계: 대표 실패 사례 비교 이미지 (요구사항 §19.A · §19.6 "demo/failure_analysis/ 에 GT와 Prediction을 비교할 수 있는 대표 이미지").

사용법 (detection-model 폴더에서 · venv 켠 뒤):
    python scripts/13_failure_images.py              # failure_analysis.csv 에 나온 사진 전부 (중복 제거)
    python scripts/13_failure_images.py --max 10     # 앞에서부터 10장만

입력:
    reports/failure_analysis.csv        실패 분석 단계 대표 실패 사례 (image 칸)
    models/baseline/baseline_best.pt    Baseline (sha 가 baseline_training_condition.md 와 같아야 함)
    data/yolo/{images,labels}/val       Val 사진 · 정답

결과:
    demo/failure_analysis/<사진이름>_compare.jpg   정답(초록) + 예측(빨강) 을 한 장에 겹친 그림   (Git 제외 · NDA · 외부 공유 금지)
    reports/failure_image_list.csv                  어떤 사진으로 그림을 만들었는지 목록 · 숫자만      (Git)

그림 읽는 법:
    초록 굵은 선  = 정답(GT) 중 모델이 맞힌 것 · 위에 Class 이름
    노랑 굵은 선  = 정답(GT) 중 모델이 놓친 것 (FN) · 위에 "MISSED Class"
    빨강 선       = 모델 예측 (conf 0.25 이상) · 아래에 "Class 확신도"
    (정답 박스는 예측 박스보다 조금 크게 그려서 두 박스가 겹쳐도 둘 다 보이게 함)
    맨 위 띠      = 파일명 · 실패 유형 · 이 사진의 TP / FP / FN

원칙:
    - Val 사진만 그린다 (Train · Test · Bridge 는 그리지 않음).
    - 회사 사진이 들어간 그림이라 demo/failure_analysis/ (Git 제외) 에만 저장한다. Discord · Figma 에 올리지 않는다.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageDraw, ImageFont
from src.manifest import read_manifest
from src.evaluate_detector import match_boxes

BEST_PT = PROJECT_ROOT / "models" / "baseline" / "baseline_best.pt"
CONDITION_MD = PROJECT_ROOT / "reports" / "baseline_training_condition.md"
FAILURE_CSV = PROJECT_ROOT / "reports" / "failure_analysis.csv"
VAL_CSV = PROJECT_ROOT / "manifests" / "val.csv"
VAL_IMAGES = PROJECT_ROOT / "data" / "yolo" / "images" / "val"
VAL_LABELS = PROJECT_ROOT / "data" / "yolo" / "labels" / "val"
OUT_DIR = PROJECT_ROOT / "demo" / "failure_analysis"
LIST_CSV = PROJECT_ROOT / "reports" / "failure_image_list.csv"

NAMES = {0: "leaf_paper", 1: "plastic_stone_metal", 2: "branch", 3: "insect",
         4: "rubber_glove_unused", 5: "disease_browning", 6: "green_onion_pepper"}
CONF, IMGSZ, IOU = 0.25, 640, 0.5          # Baseline 평가 단계 11 과 같은 기준
GT_COLOR, MISS_COLOR, PRED_COLOR = (0, 200, 70), (255, 215, 0), (230, 40, 40)
SAVE_LONG_SIDE = 1920                       # 4K 를 그대로 저장하면 무거움 → 긴 변 1920 으로 줄여 저장


def sha12(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def font(size: int):
    """한글이 없는 글자(Class 이름 · 숫자)만 쓰므로 DejaVu 로 충분. 없으면 기본 글꼴."""
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)    # Pillow 10.1 이상
    except TypeError:
        return ImageFont.load_default()


def read_gt(stem: str) -> list[tuple]:
    out = []
    for line in (VAL_LABELS / f"{stem}.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 5:
            out.append((int(parts[0]), *map(float, parts[1:])))
    return out


def to_px(box, w, h):
    """YOLO (x, y, w, h · 0~1) → 픽셀 (왼쪽 위 x, y, 오른쪽 아래 x, y)."""
    x, y, bw, bh = box
    return (x - bw / 2) * w, (y - bh / 2) * h, (x + bw / 2) * w, (y + bh / 2) * h


def draw(img: Image.Image, gts, preds, fn_idx, header: str) -> Image.Image:
    w, h = img.size
    d = ImageDraw.Draw(img)
    lw = max(3, w // 700)                    # 선 굵기: 사진 크기에 맞춰
    f = font(max(18, w // 90))
    pad = lw * 2                             # 정답 박스를 바깥으로 조금 키워서 예측 박스와 겹쳐도 보이게
    for i, g in enumerate(gts):              # 정답: 맞힘 = 초록 · 놓침 = 노랑
        x1, y1, x2, y2 = to_px(g[1:], w, h)
        missed = i in fn_idx
        color = MISS_COLOR if missed else GT_COLOR
        d.rectangle([x1 - pad, y1 - pad, x2 + pad, y2 + pad], outline=color, width=lw + 2)
        label = f"{'MISSED ' if missed else 'GT '}{NAMES.get(g[0], g[0])}"
        d.text((x1 - pad, max(0, y1 - pad - f.size - 4)), label, fill=color, font=f)
    for p in preds:                          # 예측: 빨강 선 · 박스 아래쪽에 글자 (정답 글자와 안 겹치게)
        x1, y1, x2, y2 = to_px(p[2:], w, h)
        d.rectangle([x1, y1, x2, y2], outline=PRED_COLOR, width=lw)
        d.text((x1, y2 + 2), f"{NAMES.get(p[0], p[0])} {p[1]:.2f}", fill=PRED_COLOR, font=f)
    bar = max(40, h // 25)                   # 맨 위 설명 띠
    canvas = Image.new("RGB", (w, h + bar), (25, 30, 35))
    canvas.paste(img, (0, bar))
    ImageDraw.Draw(canvas).text((12, bar // 5), header, fill=(255, 255, 255), font=font(max(20, bar // 2)))
    scale = SAVE_LONG_SIDE / max(canvas.size)
    if scale < 1:
        canvas = canvas.resize((int(canvas.width * scale), int(canvas.height * scale)))
    return canvas


def main():
    parser = argparse.ArgumentParser(description="실패 분석 단계 대표 실패 사례 비교 이미지")
    parser.add_argument("--max", type=int, default=0, help="앞에서부터 n장만 (0 = 전부)")
    args = parser.parse_args()

    # ── 검사 ────────────────────────────────────────────────────────────
    text = CONDITION_MD.read_text(encoding="utf-8") if CONDITION_MD.exists() else ""
    m = re.search(r"baseline_best\.pt` · sha `([0-9a-f]{12})`", text)
    if not BEST_PT.exists():
        sys.exit(f"[중단] 가중치가 없습니다: {BEST_PT.relative_to(PROJECT_ROOT)}")
    if not m or sha12(BEST_PT) != m.group(1):
        sys.exit("[중단] baseline_best.pt sha 가 Baseline 학습 단계 기록과 다릅니다 (다른 가중치)")
    if not FAILURE_CSV.exists():
        sys.exit("[중단] reports/failure_analysis.csv 가 없습니다")

    val_names = {r["file_name"] for r in read_manifest(VAL_CSV)[0]}
    with open(FAILURE_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    order, types = [], {}
    for r in rows:                                           # 같은 사진이 여러 행이면 유형을 모아서 한 장으로
        name = r["image"].strip()
        if name not in types:
            order.append(name)
            types[name] = []
        if r["failure_type"] not in types[name]:
            types[name].append(r["failure_type"])
    skipped = [n for n in order if n not in val_names]
    order = [n for n in order if n in val_names]           # Val 만 (Failure Analysis 는 Validation 만)
    if args.max:
        order = order[:args.max]
    print(f"그릴 사진 {len(order)}장 (failure_analysis.csv 기준 · 중복 제거)" + (f" · Val 이 아니라 건너뜀 {skipped}" if skipped else ""))

    # ── 예측 · 그리기 ─────────────────────────────────────────────────────
    from ultralytics import YOLO
    model = YOLO(str(BEST_PT))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_rows = []
    for r in model.predict(source=[str(VAL_IMAGES / n) for n in order], conf=CONF, imgsz=IMGSZ,
                           stream=True, verbose=False, save=False):
        name = Path(r.path).name
        preds = [(int(c), float(s), *map(float, b))
                 for c, s, b in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xywhn.tolist())]
        gts = read_gt(Path(name).stem)
        mb = match_boxes(gts, preds, IOU)
        header = (f"{name} | {' + '.join(types[name])} | GT {len(gts)} . pred {len(preds)} | "
                  f"TP {mb['tp']}  FP {mb['fp']}  FN {mb['fn']}  | green=GT found  yellow=GT missed  red=prediction (conf>={CONF})")
        img = Image.open(r.path).convert("RGB")
        out = OUT_DIR / f"{Path(name).stem}_compare.jpg"
        draw(img, gts, preds, set(mb["fn_idx"]), header).save(out, quality=90)
        out_rows.append({"image": name, "failure_type": " + ".join(types[name]), "gt": len(gts), "pred": len(preds),
                         "tp": mb["tp"], "fp": mb["fp"], "fn": mb["fn"], "class_err": mb["class_err"],
                         "saved_as": f"demo/failure_analysis/{out.name}"})
        print(f"  ✓ {out.name}   TP {mb['tp']} · FP {mb['fp']} · FN {mb['fn']}   ({' + '.join(types[name])})")

    with open(LIST_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)
    print(f"\n저장: demo/failure_analysis/ {len(out_rows)}장 (Git 제외 · 외부 공유 금지) · 목록 {LIST_CSV.relative_to(PROJECT_ROOT)} (Git)")
    print("Gate ②: 그림을 열어 '정답(초록)과 예측(빨강)을 비교할 수 있는지' 사람이 확인하고 체크")


if __name__ == "__main__":
    main()
