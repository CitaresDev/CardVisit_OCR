import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

# 🔐 Table 1: Authentication Credentials (Decoupled & Hashed)
# Hacker breaching this table sees ONLY hashes and UUID tokens - NO names, NO emails, NO card data!
class UserCredential(Base):
    __tablename__ = "user_credentials"

    account_token = Column(String(64), primary_key=True, default=lambda: f"usr_{uuid.uuid4().hex}")
    username_hash = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# 👤 Table 2: User Profiles (Decoupled Profile Info)
# Hacker breaching this table sees ONLY profiles - NO passwords, NO card data!
class UserProfile(Base):
    __tablename__ = "user_profiles"

    profile_id = Column(Integer, primary_key=True, autoincrement=True)
    account_token = Column(String(64), ForeignKey("user_credentials.account_token"), nullable=False, index=True)
    full_name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False)
    role = Column(String(32), default="user")
    created_at = Column(DateTime, default=datetime.utcnow)

# 🎴 Table 3: Card Records (Decoupled Card Vault)
# Hacker breaching this table sees ONLY raw card data linked to an anonymous owner_token - NO user accounts!
class CardRecord(Base):
    __tablename__ = "card_records"

    card_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_token = Column(String(64), nullable=False, index=True)  # Anonymous UUID link
    company_name = Column(Text, default="")
    full_name = Column(Text, default="")
    job_title = Column(Text, default="")
    phone = Column(String(64), default="")
    phone_2 = Column(String(64), default="")
    email = Column(String(128), default="")
    website = Column(String(255), default="")
    address = Column(Text, default="")
    tax_code = Column(String(64), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
