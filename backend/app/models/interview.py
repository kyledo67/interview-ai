from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON  # type: ignore
from datetime import datetime
from sqlalchemy.ext.mutable import MutableDict, MutableList
from app.database import Base
from sqlalchemy.orm import relationship #type: ignore

class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key = True, index = True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable = False)
    start_time = Column(DateTime, nullable=False, default = datetime.utcnow)
    end_time = Column(DateTime, nullable = True)
    scores = Column(JSON, nullable = True)
    transcript = Column(MutableList.as_mutable(JSON), nullable = True)
    status = Column(String, default="pending", nullable=False)
    resume_path = Column(String, nullable=False)
    meta_info = Column(MutableDict.as_mutable(JSON), nullable=True, default=dict)

    user = relationship("User", back_populates="interviews")
