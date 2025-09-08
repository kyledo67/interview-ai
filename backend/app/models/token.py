from sqlalchemy import Column, Integer, String, DateTime, ForeignKey  # type: ignore
from datetime import datetime
from app.database import Base
from sqlalchemy.orm import relationship #type: ignore

class RefreshToken(Base):
    __tablename__ = "refresh_token"
    id = Column(Integer, primary_key=True, index = True)
    token = Column(String, nullable=True, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) #type: ignore
    created_at = Column(DateTime, default=datetime.utcnow) 
    expire_at = Column(DateTime, nullable = False)

    user = relationship("User", back_populates="tokens")


