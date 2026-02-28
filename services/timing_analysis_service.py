from datetime import datetime, timedelta, time
from typing import Dict, Optional

from models.lifestyle_model import UserLifestyle


def _to_datetime(base: datetime, t: Optional[time]) -> Optional[datetime]:
    if not t:
        return None
    return datetime.combine(base.date(), t)


def analyze_meal_timing(
    *,
    now: datetime,
    lifestyle: Optional[UserLifestyle],
    last_meal_time: Optional[datetime],
    meal_label: Optional[str],
) -> Dict[str, str]:
    """
    Provide timing-aware guidance when a new meal/nutrition log is created.

    - If lunch logged too early vs stored lunch_time, suggest better spacing.
    - If gap between last meal and next scheduled meal > 5h, suggest snack.
    - If dinner too late relative to sleep_time, warn about impact.
    """
    advice = []
    tags = []

    if not lifestyle:
        return {"message": "", "tags": ""}

    wake_dt = _to_datetime(now, lifestyle.wake_time)
    lunch_dt = _to_datetime(now, lifestyle.lunch_time)
    dinner_dt = _to_datetime(now, lifestyle.dinner_time)
    sleep_dt = _to_datetime(now, lifestyle.sleep_time)

    # Handle potential cross‑midnight sleep for comparison
    if sleep_dt and dinner_dt and sleep_dt <= dinner_dt:
        sleep_dt = sleep_dt + timedelta(days=1)

    if meal_label and meal_label.lower() == "lunch" and lunch_dt:
        # Lunch more than 90 minutes earlier than schedule
        if now < lunch_dt - timedelta(minutes=90):
            advice.append(
                "You're having lunch quite early compared to your usual schedule. "
                "Aim to keep at least 3–4 hours after breakfast so your hunger and "
                "blood sugar patterns stay steady."
            )
            tags.append("early_lunch")

    if last_meal_time and lifestyle:
        # Next scheduled main meal after last_meal_time
        candidate_times = [
            dt for dt in [lunch_dt, dinner_dt] if dt and dt > last_meal_time
        ]
        next_meal_dt = min(candidate_times) if candidate_times else None

        if next_meal_dt and (next_meal_dt - last_meal_time) > timedelta(hours=5):
            advice.append(
                "There is a long gap (>5 hours) between this meal and your next "
                "scheduled one. Consider adding a light, high-fiber snack in between "
                "to avoid energy crashes."
            )
            tags.append("long_gap_snack_suggestion")

    if meal_label and meal_label.lower() == "dinner" and dinner_dt and sleep_dt:
        if dinner_dt > sleep_dt - timedelta(hours=2):
            advice.append(
                "Your dinner is quite close to your sleep time. Try to finish dinner "
                "at least 2–3 hours before bed to support digestion, glucose control, "
                "and sleep quality."
            )
            tags.append("late_dinner")

    return {
        "message": " ".join(advice),
        "tags": ",".join(tags),
    }

