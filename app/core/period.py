from datetime import datetime, time

# 수원대 실제 수업시간표 — 1~8교시 50분 슬롯(:30~:20), 9·10교시 야간 45분(:25~:10 / :15~:00)
# 쉬는 시간 사이사이 5~10분
PERIOD_SCHEDULE = {
    1:  (time(9, 30),  time(10, 20)),
    2:  (time(10, 30), time(11, 20)),
    3:  (time(11, 30), time(12, 20)),
    4:  (time(12, 30), time(13, 20)),
    5:  (time(13, 30), time(14, 20)),
    6:  (time(14, 30), time(15, 20)),
    7:  (time(15, 30), time(16, 20)),
    8:  (time(16, 30), time(17, 20)),
    9:  (time(17, 25), time(18, 10)),
    10: (time(18, 15), time(19, 0)),
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
