import os
import hashlib
import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.models import Base, UserCredential, UserProfile, CardRecord

# Environment DB URL (PostgreSQL on Vercel/Cloud, SQLite local fallback)
DATABASE_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Local SQLite Fallback
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "database", "card_visit.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"
elif DATABASE_URL.startswith("postgres://"):
    # Fix for Vercel/Heroku legacy postgres:// scheme
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Auto-create tables
def init_db():
    Base.metadata.create_all(bind=engine)

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper cryptographic hash functions
def hash_username(username: str) -> str:
    return hashlib.sha256(username.strip().lower().encode("utf-8")).hexdigest()

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def save_card_to_database(card_data: dict, owner_token: str = "anon_user") -> bool:
    """
    Saves card data to Table 3 (card_records) in parallel with Google Sheets.
    """
    db = SessionLocal()
    try:
        record = CardRecord(
            owner_token=owner_token,
            company_name=card_data.get("company_name", ""),
            full_name=card_data.get("full_name", ""),
            job_title=card_data.get("job_title", ""),
            phone=card_data.get("phone", ""),
            phone_2=card_data.get("phone_2", ""),
            email=card_data.get("email", ""),
            website=card_data.get("website", ""),
            address=card_data.get("address", ""),
            tax_code=card_data.get("tax_code", "")
        )
        db.add(record)
        db.commit()
        return True
    except Exception as e:
        print(f"[DB Save Error]: {e}")
        db.rollback()
        return False
    finally:
        db.close()
