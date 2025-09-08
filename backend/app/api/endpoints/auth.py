from fastapi import APIRouter, Depends, HTTPException, status # type: ignore
from sqlalchemy.orm import Session # type: ignore
from app.models.user import User
from app.models.token import RefreshToken
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user, create_refresh_token
from datetime import datetime, timedelta
from app.config import settings
from fastapi import Response, Request #type: ignore


router = APIRouter()

@router.post("/register", response_model = UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail = "Email already registered.")
    if len(user.password) <= 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail = "Password must be greater than 5 characters.")
    hashed_pw = hash_password(user.password)
    new_user = User(email = user.email, hashed_password = hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.post("/login")
def login(user_credentials: UserLogin, response: Response, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_credentials.email).first()
    if not existing_user or not verify_password(user_credentials.password, existing_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail = "Invalid Email or Password.")
    access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": str(existing_user.id)}, expires_delta=access_token_expire)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False, 
        samesite="lax",
        max_age=1800   
    )
    refresh_token = create_refresh_token(existing_user, db)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token.token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=int((refresh_token.expire_at-datetime.utcnow()).total_seconds())
    )
    #retuning refrshtoken for dev only
    return {"message": "Login successful", "refresh token": refresh_token}

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/refresh")
def refresh(response: Response, request: Request, db: Session = Depends(get_db)):
    rtoken = request.cookies.get("refresh_token")
    if not rtoken:
        raise HTTPException(status_code=401, detail="No refresh token")
    
    token = db.query(RefreshToken).filter(RefreshToken.token == rtoken).first()
    if not token or token.expire_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    # Create new access token
    access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(token.user.id)}, 
        expires_delta=access_token_expire
    )
    
    # Set new access token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    # Extend refresh token cookie (optional - keeps user logged in longer)
    response.set_cookie(
        key="refresh_token",
        value=rtoken,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=30 * 24 * 60 * 60  # 30 days
    )
    
    return {"message": "cool beans"}
    

    
    
    
