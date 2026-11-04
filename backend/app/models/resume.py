from sqlalchemy import Column, ForeignKey, Integer, LargeBinary
from app.database import Base


class Resume(Base):
    """One private resume per user, shared across function instances."""
    __tablename__ = "resumes"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    content = Column(LargeBinary, nullable=False)
