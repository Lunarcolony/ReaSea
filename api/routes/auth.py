from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserPreference
from api.schemas import RegisterRequest, TokenResponse
from api.auth_utils import hash_password, verify_password, create_access_token, require_user

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        display_name=body.display_name or body.email.split("@")[0],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(UserPreference(user_id=user.id, topic_slugs=[]))
    db.commit()
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.get("/me")
def me(user: User = Depends(require_user)):
    pref = user.preferences
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "research_role": user.research_role,
        "topic_slugs": pref.topic_slugs if pref else [],
    }
