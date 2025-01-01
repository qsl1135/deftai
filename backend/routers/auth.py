from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError

from db.database import get_db
from db.models import User, Team, TeamMember, TeamRole
from schemas.models import UserCreate, UserResponse, AuthResponse, UserUpdate
from config import JWT_SECRET_KEY, CREDITS_DEFAULT, JWT_EXPIRATION_DAYS

router = APIRouter(prefix="/api/auth", tags=["auth"])

API_KEY_HEADER = APIKeyHeader(name="Authorization")


async def get_current_user_from_token(
    token: str = Security(API_KEY_HEADER), db: Session = Depends(get_db)
):
    try:
        token = token.replace("Bearer ", "")
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/create", response_model=AuthResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Start transaction
    try:
        # Create user
        new_user = User(username=user.username)
        db.add(new_user)
        db.flush()  # Flush to get the user ID

        # Create personal team
        personal_team = Team(name=f"{user.username}'s Team", credits=CREDITS_DEFAULT)
        db.add(personal_team)
        db.flush()

        # Add user as team admin
        team_member = TeamMember(
            team_id=personal_team.id, user_id=new_user.id, role=TeamRole.ADMIN
        )
        db.add(team_member)

        db.commit()
        db.refresh(new_user)

        # Generate token
        token = jwt.encode(
            {
                "sub": new_user.username,
                "exp": datetime.now() + timedelta(days=JWT_EXPIRATION_DAYS),
            },
            JWT_SECRET_KEY,
            algorithm="HS256",
        )
        return AuthResponse(user=new_user, token=token)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(get_current_user_from_token)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):

    # Check if email is being updated and if it's already taken
    if user_update.email and user_update.email != current_user.email:
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already taken")

    if user_update.email:
        current_user.email = user_update.email

    try:
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
