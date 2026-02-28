from datetime import datetime

from extensions import db  # type: ignore


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


def init_models():
    """Import models so that SQLAlchemy is aware of them."""
    # Local imports to avoid circular dependencies
    from .user_model import User  # noqa: F401
    from .lifestyle_model import UserLifestyle  # noqa: F401
    from .nutrition_model import NutritionLog  # noqa: F401
    from .diet_model import DietRequest  # noqa: F401

