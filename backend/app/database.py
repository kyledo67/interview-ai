from sqlalchemy.orm import declarative_base, sessionmaker #type: ignore
from sqlalchemy import create_engine #type: ignore
from app.config import settings
from sqlalchemy.pool import NullPool

Base = declarative_base()
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, poolclass=NullPool)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
