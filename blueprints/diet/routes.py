from datetime import datetime
from typing import Any, Dict, Optional

from flask import Blueprint, redirect, render_template, request, session, url_for

from models.lifestyle_model import UserLifestyle
from models.user_model import User
from models.diet_model import DietRequest
from services.sleep_service import calculate_sleep_analysis
from services.prompt_builder import build_diet_prompt_payload
from services.gemini_service import generate_diet_plan
from extensions import db  # type: ignore

diet_bp = Blueprint("diet", __name__, template_folder="../../templates/diet")


def _get_current_user() -> Optional[User]:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


@diet_bp.route("/plan", methods=["GET", "POST"])
def diet_plan():
    user = _get_current_user()
    if not user:
        return redirect(url_for("auth.login"))

    lifestyle = UserLifestyle.get_lifestyle_by_user_id(user.id)

    if request.method == "POST":
        # These should match the existing health and diet input fields.
        body_data = {
            "age": request.form.get("age"),
            "gender": request.form.get("gender"),
            "height_cm": request.form.get("height"),
            "weight_kg": request.form.get("weight"),
            "activity_level": request.form.get("activity_level"),
            "primary_fitness_goal": request.form.get("primary_goal"),
            "bmi": request.form.get("bmi"),
        }

        medical_data = {
            "medical_issues": request.form.get("medical_issues"),
            "additional_notes": request.form.get("additional_notes"),
        }

        preferences = {
            "diet_preference": request.form.get("diet_preference"),
            "regional_cuisine": request.form.get("regional_cuisine"),
            "food_likes": request.form.get("food_likes"),
            "food_dislikes": request.form.get("food_dislikes"),
        }

        # Allow user overrides from the form. If user leaves these empty, fall back to stored lifestyle timings.
        def pick_time(field_name: str, lifestyle_value) -> Optional[str]:
            form_val = (request.form.get(field_name) or "").strip()
            if form_val:
                return form_val  # expected "HH:MM" from <input type="time">
            if lifestyle and lifestyle_value:
                return lifestyle_value.strftime("%H:%M")
            return None

        lifestyle_timing = {
            "wake_time": pick_time("wake_time", lifestyle.wake_time if lifestyle else None),
            "breakfast_time": pick_time("breakfast_time", lifestyle.breakfast_time if lifestyle else None),
            "lunch_time": pick_time("lunch_time", lifestyle.lunch_time if lifestyle else None),
            "snack_time": pick_time("snack_time", lifestyle.snack_time if lifestyle else None),
            "dinner_time": pick_time("dinner_time", lifestyle.dinner_time if lifestyle else None),
            "sleep_time": pick_time("sleep_time", lifestyle.sleep_time if lifestyle else None),
        }

        sleep_analysis = calculate_sleep_analysis(
            wake_time_str=lifestyle_timing.get("wake_time"),
            sleep_time_str=lifestyle_timing.get("sleep_time"),
        )

        prompt_payload: Dict[str, Any] = build_diet_prompt_payload(
            body_data=body_data,
            medical_data=medical_data,
            preferences=preferences,
            lifestyle_timing=lifestyle_timing,
            sleep_analysis=sleep_analysis,
        )

        diet_response: Dict[str, Any] = generate_diet_plan(prompt_payload)

        diet_req = DietRequest(
            user_id=user.id,
            prompt_payload=prompt_payload,
            ai_model="gemini-1.5-pro",
            response_latency_ms=None,
        )
        diet_req.response_payload = diet_response
        db.session.add(diet_req)
        db.session.commit()

        return redirect(url_for("diet.diet_plan_detail", request_id=diet_req.id))

    # GET request: just render the input form page
    return render_template(
        "diet/plan.html",
        user=user,
        lifestyle=lifestyle,
    )


@diet_bp.route("/plan/detail/<int:request_id>", methods=["GET"])
def diet_plan_detail(request_id: int):
    """Show the full diet plan on a separate page after generation."""
    user = _get_current_user()
    if not user:
        return redirect(url_for("auth.login"))

    lifestyle = UserLifestyle.get_lifestyle_by_user_id(user.id)

    diet_req: Optional[DietRequest] = DietRequest.query.get(request_id)
    if not diet_req or diet_req.user_id != user.id:
        return redirect(url_for("diet.diet_plan"))

    diet_response: Optional[Dict[str, Any]] = diet_req.response_payload
    prompt_payload: Optional[Dict[str, Any]] = diet_req.prompt_payload

    if not diet_response or not prompt_payload:
        return redirect(url_for("diet.diet_plan"))

    return render_template(
        "diet/plan_detail.html",
        user=user,
        lifestyle=lifestyle,
        diet_response=diet_response,
        prompt_payload=prompt_payload,
    )

