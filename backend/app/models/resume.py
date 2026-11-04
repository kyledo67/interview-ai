from sqlalchemy import Column, DDL, ForeignKey, Integer, LargeBinary, event
from app.database import Base


class Resume(Base):
    """One private resume per user, shared across function instances."""
    __tablename__ = "resumes"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    content = Column(LargeBinary, nullable=False)


# Supabase exposes public-schema tables through its API. Only the trusted
# backend database role should access uploaded PDFs; no public policies exist.
event.listen(
    Resume.__table__,
    "after_create",
    DDL("ALTER TABLE resumes ENABLE ROW LEVEL SECURITY").execute_if(dialect="postgresql"),
)
