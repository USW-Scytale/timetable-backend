"""수원대 시간표 문자열 파서.

입력 예:
  "종합606(화1,2,3)"                       → 1개 슬롯
  "미래103(화1,2),미래B102(화3,4)"         → 2개 슬롯 (다중 강의실)
  "(토10,11,12)"                            → 1개 슬롯, 강의실 없음 (이러닝)
"""
import re
from typing import Optional

from app.core.period import DAY_KR_SHORT_TO_EN

_SLOT_RE = re.compile(r"([^,()]*)\(([월화수목금토])([\d,]+)\)")


class TimetableParseError(ValueError):
    pass


def parse_timetable_string(s: Optional[str]) -> list[dict]:
    """시간표 문자열을 슬롯 리스트로 파싱.

    반환: [{"room": str|None, "day": "mon"~"sat", "periods": [int, ...]}, ...]
    """
    if not s or not s.strip():
        return []

    slots: list[dict] = []
    for m in _SLOT_RE.finditer(s):
        room_kr = m.group(1).strip() or None
        day_kr = m.group(2)
        periods_raw = m.group(3)

        day = DAY_KR_SHORT_TO_EN.get(day_kr)
        if day is None:
            raise TimetableParseError(f"unknown day: {day_kr!r} in {s!r}")

        periods = [int(p) for p in periods_raw.split(",") if p.strip()]
        if not periods:
            raise TimetableParseError(f"no periods parsed from {s!r}")

        slots.append({"room": room_kr, "day": day, "periods": periods})

    if not slots:
        raise TimetableParseError(f"no slots matched in {s!r}")

    return slots
