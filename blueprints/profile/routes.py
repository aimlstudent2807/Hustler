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

from extensions import db  # type: ignore
from models.user_model import User
from models.lifestyle_model import UserLifestyle

profile_bp = Blueprint("profile", __name__, template_folder="../../templates/profile")


def _get_current_user() -> Optional[User]:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


@profile_bp.route("/", methods=["GET", "POST"])
def profile():
    user = _get_current_user()
    if not user:
        return redirect(url_for("auth.login"))

    lifestyle = UserLifestyle.get_lifestyle_by_user_id(user.id)

    if request.method == "POST":
        # Existing health + diet inputs should be handled here as in the current system.
        # For now, we focus on lifestyle timing inputs while keeping the structure extensible.

        # Lifestyle timing fields (validated as HH:MM or empty)
        wake_time = request.form.get("wake_time") or None
        breakfast_time = request.form.get("breakfast_time") or None
        lunch_time = request.form.get("lunch_time") or None
        snack_time = request.form.get("snack_time") or None
        dinner_time = request.form.get("dinner_time") or None
        sleep_time = request.form.get("sleep_time") or None

        def _parse_time(value: Optional[str]):
            if not value:
                return None
            try:
                return datetime.strptime(value, "%H:%M").time()
            except ValueError:
                return None

        wake_t = _parse_time(wake_time)
        breakfast_t = _parse_time(breakfast_time)
        lunch_t = _parse_time(lunch_time)
        snack_t = _parse_time(snack_time)
        dinner_t = _parse_time(dinner_time)
        sleep_t = _parse_time(sleep_time)

        if any(v is None and (raw is not None and raw != "") for v, raw in [
            (wake_t, wake_time),
            (breakfast_t, breakfast_time),
            (lunch_t, lunch_time),
            (snack_t, snack_time),
            (dinner_t, dinner_time),
            (sleep_t, sleep_time),
        ]):
            flash("Please provide valid times in HH:MM format.", "error")
        else:
            lifestyle = UserLifestyle.save_or_update_lifestyle(
                user_id=user.id,
                wake_time=wake_t,
                breakfast_time=breakfast_t,
                lunch_time=lunch_t,
                snack_time=snack_t,
                dinner_time=dinner_t,
                sleep_time=sleep_t,
            )
            flash("Lifestyle timing updated successfully.", "success")

    return render_template(
        "profile/profile.html",
        user=user,
        lifestyle=lifestyle,
    )

