from datetime import datetime, time, timedelta
from typing import Dict, Optional

TIME_FORMAT = "%H:%M"


def _to_time(value: Optional[str]) -> Optional[time]:
    if not value:
        return None
    try:
        return datetime.strptime(value, TIME_FORMAT).time()
    except ValueError:
        return None


def calculate_sleep_analysis(
    wake_time_str: Optional[str],
    sleep_time_str: Optional[str],
) -> Dict[str, Optional[float]]:
    """
    Calculate sleep duration and qualitative status.

    Handles sleep crossing midnight, e.g. sleep_time=23:30, wake_time=06:00.
    Returns a dict with:
        - sleep_hours: float | None
        - sleep_status: 'insufficient' | 'optimal' | 'excessive' | 'unknown'
    """
    wake_time = _to_time(wake_time_str)
    sleep_time = _to_time(sleep_time_str)

    if wake_time is None or sleep_time is None:
        return {"sleep_hours": None, "sleep_status": "unknown"}

    today = datetime.today().date()
    sleep_dt = datetime.combine(today, sleep_time)
    wake_dt = datetime.combine(today, wake_time)

    if wake_dt <= sleep_dt:
        wake_dt = wake_dt + timedelta(days=1)

    duration = wake_dt - sleep_dt
    sleep_hours = round(duration.total_seconds() / 3600.0, 2)

    if sleep_hours < 7:
        status = "insufficient"
    elif 7 <= sleep_hours <= 9:
        status = "optimal"
    elif sleep_hours > 9.5:
        status = "excessive"
    else:
        status = "borderline"

    return {"sleep_hours": sleep_hours, "sleep_status": status}

