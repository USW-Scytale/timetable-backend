from datetime import datetime, time

PERIOD_SCHEDULE = {
    1: (time(9, 0), time(9, 50)),
    2: (time(10, 0), time(10, 50)),
    3: (time(11, 0), time(11, 50)),
    4: (time(12, 0), time(12, 50)),
    5: (time(13, 0), time(13, 50)),
    6: (time(14, 0), time(14, 50)),
    7: (time(15, 0), time(15, 50)),
    8: (time(16, 0), time(16, 50)),
    9: (time(17, 0), time(17, 50)),
    10: (time(18, 0), time(18, 50)),
    11: (time(19, 0), time(19, 50)),
    12: (time(20, 0), time(20, 50)),
    13: (time(21, 0), time(21, 50)),
    14: (time(22, 0), time(22, 50)),
    15: (time(23, 0), time(23, 50)),
}

PERIOD_START_TIME = {p: f"{s.strftime('%H:%M')}" for p, (s, _) in PERIOD_SCHEDULE.items()}
PERIOD_END_TIME = {p: f"{e.strftime('%H:%M')}" for p, (_, e) in PERIOD_SCHEDULE.items()}

WEEKDAY_TO_DAY = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat"}

DAY_KR = {
    "mon": "월요일", "tue": "화요일", "wed": "수요일",
    "thu": "목요일", "fri": "금요일", "sat": "토요일",
}

DAY_KR_SHORT = {
    "mon": "월", "tue": "화", "wed": "수",
    "thu": "목", "fri": "금", "sat": "토",
}

DAY_KR_SHORT_TO_EN = {v: k for k, v in DAY_KR_SHORT.items()}


def get_current_period() -> int | None:
    now = datetime.now().time()
    for period, (start, end) in PERIOD_SCHEDULE.items():
        if start <= now <= end:
            return period
    return None


def get_current_day() -> str | None:
    weekday = datetime.now().weekday()
    return WEEKDAY_TO_DAY.get(weekday)


def make_schedule_text(schedules: list) -> str:
    day_map: dict[str, list[int]] = {}
    for s in schedules:
        day_map.setdefault(s.day, []).append(s.start_period)
    parts = []
    for day, periods in day_map.items():
        start = PERIOD_START_TIME[min(periods)]
        end = PERIOD_END_TIME[max(periods)]
        parts.append(f"{DAY_KR_SHORT[day]} {start}~{end}")
    return ", ".join(parts)
