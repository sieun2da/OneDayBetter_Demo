import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def _now(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))


def _to_int(s: str, default: int) -> int:
    try:
        v = int(str(s).strip())
        return v if v > 0 else default
    except:
        return default


def _clean_drug_name(name: str) -> str:
    name = (name or "").strip()

    name = re.sub(r"^\d+\s*", "", name)
    return name


def _action_word(drug_name: str) -> str:

    if "외용" in drug_name or "점안" in drug_name:
        return "사용"
    if "내복" in drug_name:
        return "복용"
    return "복용"


def _dt_at(date: datetime, hhmm: str, tz: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime(date.year, date.month, date.day, h, m, tzinfo=ZoneInfo(tz))


def _rollover_if_past(dt: datetime, tz: str, only_if_today: bool) -> datetime:

    if only_if_today and dt <= _now(tz):
        return dt + timedelta(days=1)
    return dt


def _evenly_spaced_times(start: datetime, end: datetime, count: int) -> list[datetime]:
    if count <= 1:
        return [start]
    total_seconds = max(1, int((end - start).total_seconds()))
    step = total_seconds // (count - 1)
    return [start + timedelta(seconds=i * step) for i in range(count)]


def _extract_after_meal_minutes(inst: str) -> int | None:
    """
    '식후30분', '식후 30분', '식후1시간', '식후 1시간' 등을 찾아 분으로 변환.
    없으면 None.
    """
    s = (inst or "").replace(" ", "")
    m = re.search(r"식후(\d+)(분|시간)", s)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    return n if unit == "분" else n * 60


def med_message(name: str, action: str, inst: str) -> str:
    """
    - '식후30분'처럼 숫자가 있으면: '식사 30분 후 ... 잊지 마세요, 꼭이요!'
    - '식후1시간'이면: '식사 1시간 후 ...'
    - 그 외 '식후'는: '식사 후 ...'
    - 취침전은: '취침 전 ...'
    - fallback은: '{name} {action} 시간이에요, 꼭이요!'
    """
    inst_no_space = (inst or "").replace(" ", "")

    mins = _extract_after_meal_minutes(inst_no_space)
    if mins is not None:
        if mins % 60 == 0 and mins >= 60:
            hours = mins // 60
            when = f"식사 {hours}시간 후"
        else:
            when = f"식사 {mins}분 후"
        return f"{when} {name} {action} 잊지 마세요, 꼭이요!"

    if "식후" in inst_no_space:
        return f"식사 후 {name} {action} 잊지 마세요, 꼭이요!"

    if "취침전" in inst_no_space:
        return f"취침 전 {name} {action} 잊지 마세요, 꼭이요!"

    return f"{name} {action} 시간이에요, 꼭이요!"


def build_med_schedules(validated: dict, meal_times: dict, wake_sleep: dict, tz="Asia/Seoul"):
    """
    times_per_day / total_days를 반드시 반영해서 '총 스케줄 개수'가 초과하지 않게 만든다.
    - per_day = 1일 투여횟수
    - days = 총 투약일수
    """

    now = _now(tz)
    base_date = now

    schedules = []
    meds = validated.get("medications", [])

    for med in meds:
        raw_name = (med.get("drug_name") or "").strip()
        name = _clean_drug_name(raw_name)
        inst = (med.get("instructions") or "").strip()
        inst_compact = inst.replace(" ", "")
        action = _action_word(raw_name)

        per_day = _to_int(med.get("times_per_day", "0"), 1)
        days = _to_int(med.get("total_days", "0"), 1)

        for day_idx in range(days):
            day_date = base_date + timedelta(days=day_idx)
            only_if_today = (day_idx == 0)

     
            if "취침전" in inst_compact and "식후" in inst_compact:
                targets = [
                    _dt_at(day_date, meal_times["breakfast"], tz) + timedelta(minutes=20),
                    _dt_at(day_date, meal_times["lunch"], tz) + timedelta(minutes=20),
                    _dt_at(day_date, meal_times["dinner"], tz) + timedelta(minutes=20),
                    _dt_at(day_date, wake_sleep["sleep"], tz) - timedelta(minutes=30),
                ]
                targets = [_rollover_if_past(t, tz, only_if_today) for t in targets]
                targets = targets[:per_day]  

                for t in targets:
                    schedules.append({
                        "fire_at": t.isoformat(),
                        "type": "MED",
                        "message": med_message(name, action, inst),
                        "meta": {"drug_name": name, "rule": "after_meal_plus_before_sleep", "raw_instructions": inst, "day": day_idx + 1}
                    })
                continue

        
            mins = _extract_after_meal_minutes(inst_compact)
            if mins is not None:
                targets = [
                    _dt_at(day_date, meal_times["breakfast"], tz) + timedelta(minutes=mins),
                    _dt_at(day_date, meal_times["lunch"], tz) + timedelta(minutes=mins),
                    _dt_at(day_date, meal_times["dinner"], tz) + timedelta(minutes=mins),
                ]
                targets = [_rollover_if_past(t, tz, only_if_today) for t in targets]
                targets = targets[:per_day] 

                for t in targets:
                    schedules.append({
                        "fire_at": t.isoformat(),
                        "type": "MED",
                        "message": med_message(name, action, inst),
                        "meta": {"drug_name": name, "rule": "after_meal_numbered", "raw_instructions": inst, "day": day_idx + 1}
                    })
                continue

            if "시간마다" in inst_compact:
                start = _dt_at(day_date, wake_sleep["wake"], tz)
                end = _dt_at(day_date, wake_sleep["sleep"], tz)

                start = _rollover_if_past(start, tz, only_if_today)
                end = start.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
                if end <= start:
                    end += timedelta(days=1)

                targets = _evenly_spaced_times(start, end, per_day)

                for t in targets:
                    schedules.append({
                        "fire_at": t.isoformat(),
                        "type": "MED",
                        "message": med_message(name, action, inst),
                        "meta": {"drug_name": name, "rule": "times_per_day_spread", "raw_instructions": inst, "day": day_idx + 1}
                    })
                continue


            if "식후" in inst_compact:
                targets = [
                    _dt_at(day_date, meal_times["breakfast"], tz) + timedelta(minutes=20),
                    _dt_at(day_date, meal_times["lunch"], tz) + timedelta(minutes=20),
                    _dt_at(day_date, meal_times["dinner"], tz) + timedelta(minutes=20),
                ]
                targets = [_rollover_if_past(t, tz, only_if_today) for t in targets]
                targets = targets[:per_day]

                for t in targets:
                    schedules.append({
                        "fire_at": t.isoformat(),
                        "type": "MED",
                        "message": med_message(name, action, inst),
                        "meta": {"drug_name": name, "rule": "after_meal_default", "raw_instructions": inst, "day": day_idx + 1}
                    })
                continue


            start = _dt_at(day_date, wake_sleep["wake"], tz)
            end = _dt_at(day_date, wake_sleep["sleep"], tz)
            start = _rollover_if_past(start, tz, only_if_today)
            end = start.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
            if end <= start:
                end += timedelta(days=1)

            targets = _evenly_spaced_times(start, end, per_day)
            for t in targets:
                schedules.append({
                    "fire_at": t.isoformat(),
                    "type": "MED",
                    "message": med_message(name, action, inst),
                    "meta": {"drug_name": name, "rule": "fallback_spread", "raw_instructions": inst, "day": day_idx + 1}
                })

    return schedules