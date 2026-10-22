"""데이터 감사 단계: Audit 검사기를 시험하기 위한 '일부러 망가뜨린' 작은 데이터 만들기.

검수 완료 데이터셋에서 8쌍을 복사한 뒤, 버그를 1개씩 심는다.
검사기가 심은 버그 9개를 '정확히' 찾아내면 검사기를 믿고 900장에 돌린다.

사용법 (detection-model 폴더에서 실행):
    python scripts/02_make_audit_fixture.py
    python scripts/03_audit_subject7_final.py --fixture

※ 원본(data/subject7_final)은 읽기만 하고, 복사본(data/audit_test)만 수정한다.
※ data/ 아래라서 Git에 올라가지 않는다.
"""
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "data" / "subject7_final"
DST = PROJECT_ROOT / "data" / "audit_test"


def append_line(txt: Path, line: str) -> None:
    """TXT 끝에 한 줄을 추가한다."""
    text = txt.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        text += "\n"
    txt.write_text(text + line + "\n", encoding="utf-8")


def main():
    # 0. 이전 테스트 데이터 지우고 새로 만들기
    if DST.exists():
        shutil.rmtree(DST)
    (DST / "images").mkdir(parents=True)
    (DST / "labels").mkdir(parents=True)

    # 1. 원본에서 앞쪽 8쌍 복사 (copyfile은 내용만 복사 → 읽기 전용 권한이 따라오지 않음)
    stems = sorted(p.stem for p in (SRC / "labels").glob("*.txt"))[:8]
    if len(stems) < 8:
        raise RuntimeError(f"원본 라벨이 8개보다 적습니다: {SRC / 'labels'}")
    for s in stems:
        shutil.copyfile(SRC / "images" / f"{s}.jpg", DST / "images" / f"{s}.jpg")
        shutil.copyfile(SRC / "labels" / f"{s}.txt", DST / "labels" / f"{s}.txt")

    lbl = lambda i: DST / "labels" / f"{stems[i]}.txt"  # noqa: E731  i번째 라벨 경로

    # 2. 버그 심기 (파일 하나에 버그 하나) ------------------------------
    planted = [
        ("CLASS_RANGE",       stems[0], "Class 9 (0~6 밖)"),
        ("CENTER_RANGE",      stems[1], "x 중심 1.5"),
        ("COLUMN_COUNT",      stems[2], "4칸짜리 줄"),
        ("EMPTY_LABEL",       stems[3], "TXT 내용 전부 삭제"),
        ("MISSING_LABEL",     stems[4], "TXT 파일 삭제"),
        ("CLASS4_REVIEW",     stems[5], "Class 4 (사용 안 함)"),
        ("BBOX_OUT_OF_IMAGE", stems[6], "x 0.98 + w 0.1 → 오른쪽 경계 초과"),
        ("PARSE_ERROR",       stems[7], "숫자 대신 'abc'"),
        ("MISSING_IMAGE",     "orphan_000", "이미지 없는 TXT 추가"),
    ]
    append_line(lbl(0), "9 0.5 0.5 0.1 0.1")
    append_line(lbl(1), "0 1.5 0.5 0.1 0.1")
    append_line(lbl(2), "0 0.5 0.5 0.1")
    lbl(3).write_text("", encoding="utf-8")
    lbl(4).unlink()
    append_line(lbl(5), "4 0.5 0.5 0.1 0.1")
    append_line(lbl(6), "0 0.98 0.5 0.1 0.1")
    append_line(lbl(7), "0 abc 0.5 0.1 0.1")
    (DST / "labels" / "orphan_000.txt").write_text("0 0.5 0.5 0.1 0.1\n", encoding="utf-8")

    # 3. 심은 버그 목록 출력 → Audit 결과와 1:1로 비교
    print(f"테스트 데이터 생성: {DST}")
    print("심은 버그 (Audit이 각 1건씩, 총 9종을 찾아야 PASS):")
    for issue_type, stem, desc in planted:
        print(f"  {issue_type:<18} {stem:<24} {desc}")


if __name__ == "__main__":
    main()
