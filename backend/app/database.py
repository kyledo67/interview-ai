from sqlalchemy.orm import declarative_base, sessionmaker #type: ignore
from sqlalchemy import create_engine #type: ignore
from app.config import settings

Base = declarative_base()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()