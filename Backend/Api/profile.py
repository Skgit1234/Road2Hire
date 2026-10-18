
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from Core.database import get_db
from Core.security import SECRET_KEY, ALGORITHM
from Models.user import User

router = APIRouter(prefix="/profile", tags=["Profile"])
bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


class ProfileUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=ProfileResponse, include_in_schema=False)
@router.get("", response_model=ProfileResponse)
def get_profile(user: User = Depends(get_current_user)):
    return user


@router.patch("/", response_model=ProfileResponse, include_in_schema=False)
@router.patch("", response_model=ProfileResponse)
def update_profile(
    details: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    updates = details.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")

    for field, value in updates.items():
        if value is None or not str(value).strip():
            raise HTTPException(
                status_code=400,
                detail=f"{field} cannot be empty"
            )

    if "email" in updates:
        existing = db.query(User).filter(
            User.email == updates["email"],
            User.id != user.id
        ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Email already registered"
            )

    for field, value in updates.items():
        setattr(user, field, str(value).strip())

    try:
        db.commit()
        db.refresh(user)
    except SQLAlchemyError:
        db.rollback()
        raise
    return user
