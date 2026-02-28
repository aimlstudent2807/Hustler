from extensions import db  # type: ignore
from models import TimestampMixin


class DietRequest(TimestampMixin, db.Model):
    """Stores raw inputs and AI metadata for diet generations for analytics."""

    __tablename__ = "diet_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_payload = db.Column(db.JSON, nullable=False)
    response_payload = db.Column(db.JSON, nullable=True)
    ai_model = db.Column(db.String(128), nullable=True)
    response_latency_ms = db.Column(db.Integer, nullable=True)

