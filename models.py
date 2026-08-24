from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True)
    email = Column(String(100), unique=True)
    password = Column(String(255))

    is_verified = Column(Integer, default=0)
    otp = Column(String(6), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)


class PendingUser(Base):
    __tablename__ = "pending_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True)
    email = Column(String(100), unique=True)
    password = Column(String(255))

    otp = Column(String(6), nullable=False)
    otp_expires_at = Column(DateTime, nullable=False)


class Report(Base):
    __tablename__ = "report"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resume_text = Column(Text)
    result = Column(Text)