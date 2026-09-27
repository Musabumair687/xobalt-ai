from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Force SQLAlchemy to use the installed psycopg2 driver
DATABASE_URL = "postgresql+psycopg2://xobalt_user:xobalt_password@localhost:5432/xobalt_db"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()