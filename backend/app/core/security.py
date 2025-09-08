from passlib.context import CryptContext # type: ignore
from app.models.user import User
from app.schemas.user import UserCreate
from passlib.hash import bcrypt #type: ignore
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError #type: ignore
from app.config import settings
from fastapi import Request, HTTPException, status, Depends #type: ignore
from app.database import get_db
from sqlalchemy.orm import Session #type: ignore
from jose import JWTError #type: ignore
import uuid
from app.models.token import RefreshToken

#hashes password          algorithm            makes it so it upgrades automatically if better hashes are available
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    #returns hashed password
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    #returns if the password was correctly hashed and if it's the same password
    return bcrypt.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None ):
    #copy of data dict
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id == None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: No User ID")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token is invalid or expired")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def create_refresh_token(user: User, db: Session):
    random_refresh_token = str(uuid.uuid4())
    expireat = datetime.utcnow() + timedelta(days=120)
    refreshtoken = RefreshToken(user_id = user.id, token=random_refresh_token, expire_at=expireat)
    db.add(refreshtoken)
    db.commit()
    return refreshtoken






    