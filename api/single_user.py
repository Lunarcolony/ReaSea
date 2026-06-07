"""Single local user — no sign-in required."""

from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserPreference

DEFAULT_EMAIL = "local@research-feed.local"
DEFAULT_NAME = "Research Reader"
DEFAULT_TOPICS = [
    "machine-learning",
    "deep-learning",
    "artificial-intelligence",
]


def ensure_default_user(db: Session) -> User:
    user = db.query(User).filter(User.email == DEFAULT_EMAIL).first()
    if not user:
        user = User(
            email=DEFAULT_EMAIL,
            hashed_password="",
            display_name=DEFAULT_NAME,
            research_role="researcher",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        pref = UserPreference(user_id=user.id, topic_slugs=DEFAULT_TOPICS)
        db.add(pref)
        db.commit()
    elif not db.query(UserPreference).filter(UserPreference.user_id == user.id).first():
        db.add(UserPreference(user_id=user.id, topic_slugs=DEFAULT_TOPICS))
        db.commit()
        db.refresh(user)
    return user


def get_default_user(db: Session = Depends(get_db)) -> User:
    return ensure_default_user(db)
