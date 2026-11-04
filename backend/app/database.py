from sqlalchemy.orm import declarative_base, sessionmaker #type: ignore
from sqlalchemy import create_engine #type: ignore
from sqlalchemy.engine import make_url
from app.config import settings
from sqlalchemy.pool import NullPool

Base = declarative_base()
database_url = make_url(settings.DATABASE_URL)
if database_url.drivername in ("postgres", "postgresql"):
    # Match the installed psycopg2-binary dependency instead of relying on
    # SQLAlchemy's version-dependent default PostgreSQL driver.
    database_url = database_url.set(drivername="postgresql+psycopg2")
engine = create_engine(database_url, pool_pre_ping=True, poolclass=NullPool)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
