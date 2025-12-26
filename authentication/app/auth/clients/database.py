import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_DB = os.getenv("POSTGRES_DB")

postgres_password_file = os.getenv("POSTGRES_PASSWORD_FILE")
if postgres_password_file:
    with open(postgres_password_file, 'r') as f:
        POSTGRES_PASSWORD = f.read().strip()

# DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5432/{POSTGRES_DB}"
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres:5432/{POSTGRES_DB}"

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