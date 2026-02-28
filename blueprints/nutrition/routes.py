from datetime import datetime
from typing import Optional

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from models.user_model import User
from services.nutrition_service import (
    aggregate_daily_nutrition,
    create_nutrition_log,
    get_daily_meal_logs,
)
from services.gemini_service import analyze_meal_from_image

nutrition_bp = Blueprint(
    "nutrition", __name__, template_folder="../../templates/nutrition"
)


def _get_current_user() -> Optional[User]:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


@nutrition_bp.route("/tracker", methods=["GET", "POST"])
def tracker():
    user = _get_current_user()
    if not user:
        return redirect(url_for("auth.login"))

    created_log = None
    analysis = None
    timing_feedback = {}
    day_totals = {}
    next_meal_plan = None

    if request.method == "POST":
        meal_label = request.form.get("meal_label") or None
        image_file = request.files.get("meal_image")

        if not image_file or image_file.filename == "":
            flash("Please upload a meal photo.", "danger")
            return redirect(url_for("nutrition.tracker"))

        image_bytes = image_file.read()
        mime_type = image_file.mimetype or "image/jpeg"

        analysis = analyze_meal_from_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            meal_label=meal_label,
        )

        metrics = analysis.get("metrics", {}) or {}
        ai_food_summary = analysis.get("summary") or ""
        ai_guidance = analysis.get("guidance") or ""

        result = create_nutrition_log(
            user=user,
            meal_label=meal_label,
            metrics=metrics,
            ai_food_summary=ai_food_summary,
            ai_guidance=ai_guidance,
            image_path=None,
        )
        created_log = result["log"]
        day_totals = result["day_totals"]
        timing_feedback = result["timing_feedback"]
        next_meal_plan = result.get("next_meal_plan")

        flash("Meal analysed and logged successfully.", "success")

    # Use local server time (IST on your machine) so "today" matches
    # your wall‑clock day when aggregating and listing meals.
    today = datetime.now()

    if not day_totals:
        day_totals = aggregate_daily_nutrition(user, today)

    today_logs = get_daily_meal_logs(user, today)

    return render_template(
        "nutrition/tracker.html",
        user=user,
        created_log=created_log,
        timing_feedback=timing_feedback,
        day_totals=day_totals,
        analysis=analysis,
        next_meal_plan=next_meal_plan,
        meal_logs=today_logs,
    )

