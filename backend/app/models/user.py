from sqlalchemy import Column, Integer, String, DateTime, Boolean # type: ignore
from datetime import datetime
from app.database import Base
from sqlalchemy.orm import relationship #type: ignore

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key = True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete")
    interviews = relationship("Interview", back_populates="user", cascade="all, delete")