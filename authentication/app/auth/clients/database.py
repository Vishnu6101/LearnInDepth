from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql://auth_user:auth_pass@localhost:5432/auth_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

# This makes sure that one session is created for each request to DB and is closed immediately
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()