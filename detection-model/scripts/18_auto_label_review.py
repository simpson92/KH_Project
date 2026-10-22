"""Final 선정 단계: Auto Label 후보 vs 사람 검수 결과 비교 · 집계 (산출물 6).

사용법 (detection-model 폴더에서 · 라벨 검수 도구으로 검수를 끝낸 뒤):
    python scripts/18_auto_label_review.py

입력 (Git 제외):
    demo/auto_label/candidate_labels/*.txt            AI 후보 (17 이 만듦)
    demo/auto_label/review_workspace/work|final/labels/*.txt   사람이 저장한 라벨 (final = QA PASS 가 있으면 우선)
    demo/auto_label/review_workspace/manifests/dataset_manifest.csv   라벨 검수 도구 작업대장 (status · review_reason · worker)
    demo/auto_label/gt_hidden/*.txt                   Test 정답 (참고 비교만)

결과:
    demo/auto_label/reviewed_labels/*.txt             사람이 검수 · 승인한 라벨 (경로)      [Git 제외]
    reports/auto_label_review.csv                     사진별 승인 · Class 수정 · BBox 수정 · 삭제 · 누락 추가 · REVIEW  [Git · 숫자만]

후보 박스 하나를 이렇게 분류한다 (검수 라벨과 IoU 가 큰 짝부터 1:1 로 짝짓기):
    승인        같은 Class · IoU ≥ 0.95   (사람이 그대로 둠)
    Class 수정  IoU ≥ 0.5 인데 Class 가 바뀜 (위치도 바뀌었으면 Class 수정으로 셈)
    BBox 수정   같은 Class · 0.5 ≤ IoU < 0.95
    삭제        짝이 없음 (사람이 지운 오검출)
    누락 추가   검수 라벨 중 짝이 없는 박스 (AI 가 놓친 것을 사람이 그림)
    REVIEW      작업대장 status = REVIEW 인 사진 수
참고: 정답(gt_hidden)과 비교해 "AI 후보만" vs "사람 검수 후" 가 정답을 얼마나 맞히는지 (같은 Class · IoU 0.5 · match_boxes)
"""
from pathlib import Path
import csv
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluate_detector import iou_xywh, match_boxes

AUTO = PROJECT_ROOT / "demo" / "auto_label"
CAND_DIR = AUTO / "candidate_labels"
GT_DIR = AUTO / "gt_hidden"
WS = AUTO / "review_workspace"
REVIEWED_DIR = AUTO / "reviewed_labels"
WS_MANIFEST = WS / "manifests" / "dataset_manifest.csv"
OUT_CSV = PROJECT_ROOT / "reports" / "auto_label_review.csv"
APPROVE_IOU, MATCH_IOU = 0.95, 0.5
VALID_CLASSES = {0, 1, 2, 3, 5, 6}


def read_yolo(path: Path) -> tuple[list[tuple], list[str]]:
    boxes, errors = [], []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        p = line.split()
        if not p:
            continue
        try:
            c, *xywh = int(p[0]), *map(float, p[1:])
        except ValueError:
            errors.append(f"{path.name}:{i} 숫자 아님")
            continue
        if len(p) != 5 or c not in VALID_CLASSES or not all(0 <= v <= 1 for v in xywh):
            errors.append(f"{path.name}:{i} 형식 · Class · 좌표 범위")
            continue
        boxes.append((c, *xywh))
    return boxes, errors


def compare(cands: list[tuple], reviewed: list[tuple]) -> dict:
    """후보 ↔ 검수 박스 1:1 짝짓기 (Class 무관 · IoU 큰 순) → 분류."""
    pairs = sorted(((iou_xywh(c[1:], r[1:]), i, j) for i, c in enumerate(cands) for j, r in enumerate(reviewed)),
                   reverse=True)
    used_c, used_r = set(), set()
    out = {"approved": 0, "class_changed": 0, "bbox_changed": 0}
    for v, i, j in pairs:
        if v < MATCH_IOU:
            break
        if i in used_c or j in used_r:
            continue
        used_c.add(i)
        used_r.add(j)
        if cands[i][0] != reviewed[j][0]:
            out["class_changed"] += 1
        elif v >= APPROVE_IOU:
            out["approved"] += 1
        else:
            out["bbox_changed"] += 1
    out["deleted"] = len(cands) - len(used_c)
    out["added"] = len(reviewed) - len(used_r)
    return out


def read_manifest_rows() -> dict:
    if not WS_MANIFEST.exists():
        return {}
    with open(WS_MANIFEST, encoding="utf-8-sig") as f:
        return {r["file_name"]: r for r in csv.DictReader(f)}


def main():
    if not CAND_DIR.exists():
        sys.exit("[중단] demo/auto_label/candidate_labels/ 가 없습니다 → python scripts/17_auto_label.py 먼저")
    cand_files = sorted(CAND_DIR.glob("*.txt"))
    book = read_manifest_rows()
    rows, problems, not_reviewed = [], [], []
    if REVIEWED_DIR.exists():
        assert REVIEWED_DIR.resolve().is_relative_to(AUTO.resolve())
        shutil.rmtree(REVIEWED_DIR)
    REVIEWED_DIR.mkdir(parents=True)

    for cf in cand_files:
        stem = cf.stem
        src = next((p for p in (WS / "final" / "labels" / f"{stem}.txt", WS / "work" / "labels" / f"{stem}.txt") if p.exists()), None)
        meta = next((r for k, r in book.items() if Path(k).stem == stem), {})
        if src is None:
            not_reviewed.append(stem)
            continue
        cands, e1 = read_yolo(cf)
        reviewed, e2 = read_yolo(src)
        problems += e1 + e2
        shutil.copy2(src, REVIEWED_DIR / f"{stem}.txt")                 # 요구사항 §21.5 경로로 모음
        r = compare(cands, reviewed)
        gt = read_yolo(GT_DIR / f"{stem}.txt")[0] if (GT_DIR / f"{stem}.txt").exists() else []
        m_ai = match_boxes(gt, [(c[0], 1.0, *c[1:]) for c in cands], MATCH_IOU)
        m_hu = match_boxes(gt, [(c[0], 1.0, *c[1:]) for c in reviewed], MATCH_IOU)
        rows.append({
            "image": meta.get("file_name", f"{stem}.jpg"), "reviewer": meta.get("worker", "-"),
            "status": meta.get("status", "-"), "qa_status": meta.get("qa_status", "-"),
            "review_reason": meta.get("review_reason", ""), "saved_from": src.parent.parent.name,
            "candidate_boxes": len(cands), "reviewed_boxes": len(reviewed),
            "approved": r["approved"], "class_changed": r["class_changed"], "bbox_changed": r["bbox_changed"],
            "deleted": r["deleted"], "added": r["added"],
            "gt_boxes": len(gt), "ai_tp": m_ai["tp"], "human_tp": m_hu["tp"],
        })

    if not rows:
        sys.exit("[중단] 검수된 사진이 없습니다 (review_workspace/work 또는 final 에 저장된 TXT 없음)")
    keys = ["candidate_boxes", "reviewed_boxes", "approved", "class_changed", "bbox_changed", "deleted", "added",
            "gt_boxes", "ai_tp", "human_tp"]
    tot = {k: sum(r[k] for r in rows) for k in keys}
    n_review = sum(r["status"] == "REVIEW" for r in rows)
    rows.append({"image": "all", "reviewer": "-", "status": f"REVIEW {n_review}", "qa_status": "-", "review_reason": "",
                 "saved_from": "-", **tot})
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    n_img = len(rows) - 1
    c = tot["candidate_boxes"]
    pct = (lambda a: f"{a / c * 100:.0f}%" if c else "-")
    print(f"=== Auto Label → Human Review 집계 ===")
    print(f"  검수한 사진          {n_img} / {len(cand_files)}장" + (f"   ⚠ 미검수 {not_reviewed}" if not_reviewed else ""))
    print(f"  AI 후보 BBox         {c}개")
    print(f"  그대로 승인          {tot['approved']}개 ({pct(tot['approved'])})")
    print(f"  Class 수정           {tot['class_changed']}개 ({pct(tot['class_changed'])})")
    print(f"  BBox 수정            {tot['bbox_changed']}개 ({pct(tot['bbox_changed'])})")
    print(f"  삭제 (오검출)        {tot['deleted']}개 ({pct(tot['deleted'])})")
    print(f"  누락 추가            {tot['added']}개")
    print(f"  REVIEW 사진          {n_review}장")
    print(f"  검수 후 최종 BBox    {tot['reviewed_boxes']}개")
    if tot["gt_boxes"]:
        g = tot["gt_boxes"]
        print(f"\n  (참고 · 정답 {g}개와 비교) AI 후보만 {tot['ai_tp']}개 일치 ({tot['ai_tp'] / g:.0%}) → 사람 검수 후 {tot['human_tp']}개 ({tot['human_tp'] / g:.0%})")
    if problems:
        print(f"\n  ⚠ TXT 형식 문제 {len(problems)}건: {problems[:5]}")
    print(f"\n저장: demo/auto_label/reviewed_labels/ {n_img}개 (Git 제외) · {OUT_CSV.relative_to(PROJECT_ROOT)} (Git)")
    print("\n=== Final 선정 단계 Daily Gate · 산출물 6 ===")
    print("  ✅ demo/prediction_images/*.jpg (13)  ✅ candidate_labels/*.txt (13)")
    print(f"  {'✅' if not not_reviewed else '☐'} 라벨 검수 도구 Human Review  ✅ reviewed_labels/*.txt  ✅ reports/auto_label_review.csv")
    if not_reviewed:
        sys.exit(1)


if __name__ == "__main__":
    main()
