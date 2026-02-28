from datetime import datetime
from typing import Any, Dict, Optional

from flask import current_app

from extensions import db  # type: ignore
from models.nutrition_model import NutritionLog
from models.user_model import User
from models.lifestyle_model import UserLifestyle
from services.timing_analysis_service import analyze_meal_timing


def aggregate_daily_nutrition(user: User, day: datetime) -> Dict[str, float]:
    """Compute total macros for a given day."""
    start = datetime(day.year, day.month, day.day)
    end = start.replace(hour=23, minute=59, second=59)
    logs = (
        NutritionLog.query.filter(
            NutritionLog.user_id == user.id,
            NutritionLog.logged_at >= start,
            NutritionLog.logged_at <= end,
        )
        .order_by(NutritionLog.logged_at.asc())
        .all()
    )

    totals = {
        "calories": 0.0,
        "protein": 0.0,
        "carbs": 0.0,
        "fats": 0.0,
        "sugar": 0.0,
        "fiber": 0.0,
    }
    for log in logs:
        for key in totals:
            value = getattr(log, key)
            if value is not None:
                totals[key] += float(value)
    return totals


def get_daily_meal_logs(user: User, day: datetime) -> list[NutritionLog]:
    """Return all meals logged for a given day (chronological)."""
    start = datetime(day.year, day.month, day.day)
    end = start.replace(hour=23, minute=59, second=59)
    return (
        NutritionLog.query.filter(
            NutritionLog.user_id == user.id,
            NutritionLog.logged_at >= start,
            NutritionLog.logged_at <= end,
        )
        .order_by(NutritionLog.logged_at.asc())
        .all()
    )


def _build_next_meal_plan(
    *,
    log: NutritionLog,
    day_totals: Dict[str, float],
    lifestyle: Optional[UserLifestyle],
) -> Dict[str, Any]:
    """
    Derive simple, rule-based next‑meal suggestions from the last meal + day totals.

    This runs even in offline mode so the user always sees dynamic guidance.
    """
    meal_label = (log.meal_label or "").lower()

    total_cals_meal = float(log.calories or 0.0)
    p_cals = float(log.protein or 0.0) * 4.0
    c_cals = float(log.carbs or 0.0) * 4.0
    f_cals = float(log.fats or 0.0) * 9.0
    total_macro_cals = max(total_cals_meal, p_cals + c_cals + f_cals, 1.0)

    pc = (p_cals / total_macro_cals) * 100.0
    cc = (c_cals / total_macro_cals) * 100.0
    fc = (f_cals / total_macro_cals) * 100.0

    flags = []
    if pc < 20:
        flags.append("low_protein")
    if cc > 55:
        flags.append("high_carbs")
    if fc > 35:
        flags.append("high_fats")

    daily_cals = float(day_totals.get("calories") or 0.0)
    # Very rough reference window for daily calories; this is only used
    # to phrase guidance, not for strict tracking.
    lower_ref, upper_ref = 1600.0, 2300.0

    if daily_cals < lower_ref * 0.6:
        day_state = "low"
    elif daily_cals > upper_ref:
        day_state = "high"
    else:
        day_state = "moderate"

    # Decide the *next* meal slot in a simple Indian pattern:
    # breakfast → lunch → evening snack → dinner → next‑day breakfast.
    if meal_label == "breakfast":
        target_meal = "lunch"
    elif meal_label == "lunch":
        target_meal = "evening snack"
    elif meal_label == "snack":
        target_meal = "dinner"
    elif meal_label == "dinner":
        target_meal = "breakfast"
    else:
        target_meal = "next meal"

    pretty_target = {
        "breakfast": "breakfast",
        "lunch": "lunch",
        "evening snack": "evening snack",
        "dinner": "dinner",
    }.get(target_meal, "next meal")

    parts = []
    if "low_protein" in flags:
        parts.append(
            "This plate was on the lighter side for protein. Anchor your next plate around a solid protein source."
        )
    else:
        parts.append(
            "Protein was fairly reasonable here. You can keep protein steady and tune carbs/fats in the next plate."
        )

    if "high_carbs" in flags:
        parts.append(
            "Carbs were on the higher side, so keep the next plate grain‑light and vegetable‑heavy."
        )
    if "high_fats" in flags:
        parts.append(
            "Fats were relatively higher, so prefer grilled/steamed options instead of deep‑fried items next."
        )

    if daily_cals == 0:
        parts.append(
            "This looks like your first logged meal of the day; build the rest of the day around steady protein and vegetables."
        )
    elif day_state == "low":
        parts.append(
            "Overall, your calories today are on the lower side — a slightly fuller but still balanced next plate is okay."
        )
    elif day_state == "high":
        parts.append(
            "You are already quite high on total calories today; make the next plate lighter and avoid extra sugary drinks or desserts."
        )
    else:
        parts.append(
            "Your overall day looks moderate so far; focus on quality foods and portion control rather than strict restriction."
        )

    lifestyle_hint = ""
    if lifestyle and getattr(lifestyle, "dinner_time", None) and getattr(
        lifestyle, "sleep_time", None
    ):
        try:
            dinner_hour = lifestyle.dinner_time.hour  # type: ignore[union-attr]
            sleep_hour = lifestyle.sleep_time.hour  # type: ignore[union-attr]
            if dinner_hour >= sleep_hour - 2:
                lifestyle_hint = (
                    " Try to keep the last substantial plate at least 2–3 hours before your usual sleep time."
                )
        except Exception:
            lifestyle_hint = ""

    summary = (
        f"Based on this {meal_label or 'meal'} and your day so far, "
        f"aim for your next {pretty_target} to be protein‑anchored, veggie‑heavy and portion‑aware."
    )
    if lifestyle_hint:
        summary += lifestyle_hint

    suggestions: list[str] = []

    def _extend(items: list[str]) -> None:
        suggestions.extend(items)

    if target_meal in {"breakfast"}:
        base_items = [
            "Upma/poha with lots of vegetables (1 medium bowl) + a side of curd/Greek yogurt (1/2 cup).",
            "2–3 idlis with sambar + coconut chutney, or 2 stuffed parathas with curd and salad.",
        ]
        if "low_protein" in flags:
            base_items.append(
                "Add boiled eggs (2) OR a bowl of sprouts/chana along with your usual breakfast."
            )
        _extend(base_items)
    elif target_meal in {"lunch", "evening snack"}:
        base_items = [
            "2 phulka/chapati + 1 bowl dal/rajma/chole + 1 big bowl mixed salad (cucumber, carrot, tomato).",
            "1 cup rice + grilled/sauteed paneer/tofu/chicken (palm‑size) + 1–2 bowls vegetables.",
        ]
        if "low_protein" in flags:
            base_items.append(
                "Keep grain portion to 1 roti or 1/2 cup rice and make room for extra dal/curd or an egg/chicken side."
            )
        if "high_carbs" in flags:
            base_items.append(
                "Switch to mostly sabzi + dal with just 1 small roti; avoid extra rice, sweets and sugary drinks."
            )
        _extend(base_items)
    elif target_meal == "dinner":
        base_items = [
            "Moong dal khichdi (1 medium bowl) + salad + small bowl curd.",
            "Grilled/sauteed paneer/tofu/chicken (palm‑size) + 1–2 bowls vegetables + 1 small phulka or 1/2 cup rice.",
        ]
        if "low_protein" in flags:
            base_items.append(
                "If dinners are usually light on protein, add a bowl of dal or curd or an egg side instead of extra roti/rice."
            )
        if "high_carbs" in flags:
            base_items.append(
                "Keep grains very light at dinner (1 small phulka or 1/2 cup rice) and fill the plate with sabzi and protein."
            )
        if "high_fats" in flags:
            base_items.append(
                "Prefer home‑style gravies with less oil, tandoori/roasted options, and avoid deep‑fried starters."
            )
        _extend(base_items)
    else:
        _extend(
            [
                "Pick a plate where half the space is colourful vegetables, one‑quarter lean protein and one‑quarter whole grains.",
                "Keep a glass of water, buttermilk or unsweetened tea with the meal instead of juice or soda.",
            ]
        )

    return {
        "summary": " ".join(parts) if parts else summary,
        "headline": summary,
        "suggestions": suggestions,
    }


def create_nutrition_log(
    *,
    user: User,
    meal_label: Optional[str],
    metrics: Dict[str, Any],
    ai_food_summary: str,
    ai_guidance: str,
    image_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a nutrition log and return analytics + timing guidance."""
    # Use local server time (IST on your machine) so logged meal
    # timestamps and day summaries match what you see on the clock.
    now = datetime.now()
    lifestyle = UserLifestyle.get_lifestyle_by_user_id(user.id)

    last_log = (
        NutritionLog.query.filter_by(user_id=user.id)
        .order_by(NutritionLog.logged_at.desc())
        .first()
    )
    last_meal_time = last_log.logged_at if last_log else None

    log = NutritionLog(
        user_id=user.id,
        meal_label=meal_label,
        logged_at=now,
        image_path=image_path,
        calories=metrics.get("calories"),
        protein=metrics.get("protein"),
        carbs=metrics.get("carbs"),
        fats=metrics.get("fats"),
        sugar=metrics.get("sugar"),
        fiber=metrics.get("fiber"),
        ai_food_summary=ai_food_summary,
        ai_guidance=ai_guidance,
    )
    db.session.add(log)
    db.session.commit()

    timing_feedback = analyze_meal_timing(
        now=now,
        lifestyle=lifestyle,
        last_meal_time=last_meal_time,
        meal_label=meal_label,
    )

    day_totals = aggregate_daily_nutrition(user=user, day=now)
    next_meal_plan = _build_next_meal_plan(
        log=log,
        day_totals=day_totals,
        lifestyle=lifestyle,
    )

    return {
        "log": log,
        "day_totals": day_totals,
        "timing_feedback": timing_feedback,
        "next_meal_plan": next_meal_plan,
    }

