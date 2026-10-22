"""데이터 감사 단계 촬영 시각 · capture_group(촬영 세션) 함수 모음.

비슷한 장면(몇 초 간격으로 연속 촬영한 사진)이 Train과 Test에 나뉘어 들어가면
모델이 "외운 장면"으로 시험을 보게 됩니다 (Data Leakage).
그래서 촬영 시각이 가까운 사진을 하나의 묶음(capture_group)으로 만들고,
4단계 Split 때 묶음 단위로만 나눕니다.

    파일명 예: 250410_180800068444.jpg
               ──┬── ──┬─── ──┬───
              YYMMDD HHMMSS  마이크로초(6자리)
    ※ 파일명 = 촬영 시각이라는 것은 '추정'이다 → EXIF로 확인한다.
"""
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


def parse_capture_time(file_name: str) -> datetime:
    """파일명에서 촬영 시각을 꺼낸다. 형식이 다르면 ValueError."""
    stem = Path(file_name).stem                     # 확장자 제거: 250410_180800068444
    date_part, _, time_part = stem.partition("_")   # '_' 기준으로 앞(날짜) / 뒤(시각)
    if len(date_part) != 6 or len(time_part) != 12 or not time_part.isdigit():
        raise ValueError(f"예상과 다른 파일명 형식: {file_name}")
    base = datetime.strptime(date_part + time_part[:6], "%y%m%d%H%M%S")
    return base + timedelta(microseconds=int(time_part[6:]))


def assign_capture_groups(times: pd.Series, gap_minutes: float) -> pd.Series:
    """촬영 시각 순으로 줄 세운 뒤, 앞 사진과 gap_minutes 넘게 벌어지면 새 묶음을 시작한다.

    Args:
        times       : 이미지별 촬영 시각 (datetime)
        gap_minutes : 세션 경계 기준 (분)
    Returns:
        이미지별 그룹 번호 (원래 순서 그대로, 1부터 시작)
    """
    order = times.sort_values()
    gap = order.diff()                                       # 바로 앞 사진과의 시간 차
    is_new = gap.isna() | (gap > pd.Timedelta(minutes=gap_minutes))
    group_no = is_new.cumsum()                               # True가 나올 때마다 번호 +1
    return group_no.reindex(times.index)                     # 원래 행 순서로 되돌림


def nearest_gap_seconds(target: pd.Series, reference: pd.Series) -> pd.Series:
    """target 각 사진과 가장 가까운 reference 사진 사이의 시간 차(초)."""
    # 시각을 '나노초 정수'로 바꾸면 빼기 · 절댓값 계산을 한 번에 할 수 있음
    ref_ns = np.asarray(reference.to_numpy(dtype="datetime64[ns]").astype("int64"))
    out = []
    for t in target:
        # 모든 reference와의 시간 차 중 가장 작은 값 (900장이라 단순 반복으로 충분)
        out.append(np.abs(ref_ns - t.value).min() / 1e9)
    return pd.Series(out, index=target.index)
