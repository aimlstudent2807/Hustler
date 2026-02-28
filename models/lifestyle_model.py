from datetime import time
from typing import Optional

from extensions import db  # type: ignore
from models import TimestampMixin


class UserLifestyle(TimestampMixin, db.Model):
    __tablename__ = "user_lifestyle"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    wake_time = db.Column(db.Time, nullable=True)
    breakfast_time = db.Column(db.Time, nullable=True)
    lunch_time = db.Column(db.Time, nullable=True)
    snack_time = db.Column(db.Time, nullable=True)
    dinner_time = db.Column(db.Time, nullable=True)
    sleep_time = db.Column(db.Time, nullable=True)

    user = db.relationship("User", back_populates="lifestyle")

    @staticmethod
    def get_lifestyle_by_user_id(user_id: int) -> Optional["UserLifestyle"]:
        return UserLifestyle.query.filter_by(user_id=user_id).first()

    @staticmethod
    def save_or_update_lifestyle(
        user_id: int,
        wake_time: Optional[time],
        breakfast_time: Optional[time],
        lunch_time: Optional[time],
        snack_time: Optional[time],
        dinner_time: Optional[time],
        sleep_time: Optional[time],
    ) -> "UserLifestyle":
        lifestyle = UserLifestyle.get_lifestyle_by_user_id(user_id)
        if lifestyle is None:
            lifestyle = UserLifestyle(user_id=user_id)
            db.session.add(lifestyle)

        lifestyle.wake_time = wake_time
        lifestyle.breakfast_time = breakfast_time
        lifestyle.lunch_time = lunch_time
        lifestyle.snack_time = snack_time
        lifestyle.dinner_time = dinner_time
        lifestyle.sleep_time = sleep_time

        db.session.commit()
        return lifestyle

