from extensions import db  # type: ignore
from models import TimestampMixin


class NutritionLog(TimestampMixin, db.Model):
    __tablename__ = "nutrition_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    meal_label = db.Column(db.String(64), nullable=True)
    logged_at = db.Column(db.DateTime, nullable=False)
    image_path = db.Column(db.String(512), nullable=True)

    calories = db.Column(db.Float, nullable=True)
    protein = db.Column(db.Float, nullable=True)
    carbs = db.Column(db.Float, nullable=True)
    fats = db.Column(db.Float, nullable=True)
    sugar = db.Column(db.Float, nullable=True)
    fiber = db.Column(db.Float, nullable=True)

    ai_food_summary = db.Column(db.Text, nullable=True)
    ai_guidance = db.Column(db.Text, nullable=True)

    user = db.relationship("User", back_populates="nutrition_logs")

