import os
import hashlib
import hmac
import jwt
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.models import Base, UserCredential, UserProfile, CardRecord

# Environment DB URL (PostgreSQL on Vercel/Neon/Cloud)
DATABASE_URL = (
    os.getenv("POSTGRES_DATABASE_URL") or
    os.getenv("POSTGRES_URL") or
    os.getenv("DATABASE_URL") or
    os.getenv("STORAGE_URL") or
    os.getenv("NEON_URL") or
    os.getenv("NEON_DATABASE_URL") or
    os.getenv("POSTGRES_PRISMA_URL")
)
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "citares_secure_jwt_secret_key_2026_pro")
JWT_ALGORITHM = "HS256"

if not DATABASE_URL:
    if os.getenv("VERCEL") or os.getenv("VERCEL_ENV"):
        # Temporary /tmp SQLite DB for Vercel if Vercel Postgres is not connected yet
        DATABASE_URL = "sqlite:////tmp/card_visit.db"
    else:
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

try:
    import bcrypt
    has_bcrypt = True
except ImportError:
    has_bcrypt = False

# Helper cryptographic hash & JWT functions
def hash_username(username: str) -> str:
    return hashlib.sha256(username.strip().lower().encode("utf-8")).hexdigest()

def hash_password(password: str) -> str:
    if has_bcrypt:
        try:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        except Exception:
            pass
    # Fallback to Built-in Python hashlib PBKDF2 HMAC (Zero C-dependency)
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"pbkdf2:{salt.hex()}:{pw_hash.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    if hashed.startswith("pbkdf2:"):
        parts = hashed.split(":")
        if len(parts) == 3:
            salt = bytes.fromhex(parts[1])
            expected_hash = parts[2]
            pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
            return hmac.compare_digest(pw_hash.hex(), expected_hash)
    if has_bcrypt:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False
    return False

def create_jwt_token(account_token: str) -> str:
    payload = {
        "sub": account_token,
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None

def seed_default_user():
    admin_user = os.getenv("DEFAULT_ADMIN_USER", "CITARES")
    admin_pass = os.getenv("DEFAULT_ADMIN_PASS", "123456")
    try:
        # Guarantee tables exist on PostgreSQL / SQLite
        Base.metadata.create_all(bind=engine)
    except Exception as table_err:
        print(f"[DB Init Error]: {table_err}")

    db = SessionLocal()
    try:
        u_hash = hash_username(admin_user)
        existing = db.query(UserCredential).filter(UserCredential.username_hash == u_hash).first()
        if not existing:
            # Create Seed Account with hashed password
            p_hash = hash_password(admin_pass)
            cred = UserCredential(username_hash=u_hash, password_hash=p_hash)
            db.add(cred)
            db.commit()
            db.refresh(cred)

            prof = UserProfile(
                account_token=cred.account_token,
                full_name="CITARES Admin",
                email="admin@citares.edu.vn",
                role="admin"
            )
            db.add(prof)
            db.commit()
            print("[DB Seed]: Default account CITARES / 123456 created successfully!")
    except Exception as e:
        print(f"[DB Seed Error]: {e}")
        db.rollback()
    finally:
        db.close()

# Auto-create tables & seed default CITARES user
def init_db():
    seed_default_user()

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_card_to_database(card_data: dict, owner_token: str = "anon_user", scanned_by: str = "") -> bool:
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
            tax_code=card_data.get("tax_code", ""),
            scanned_by=scanned_by or card_data.get("scanned_by", "")
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
