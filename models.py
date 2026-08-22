from sqlalchemy import Column, Integer, String, Text ,ForeignKey
from db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True)
    password = Column(String(255), nullable=False)
    
class Report(Base):
    __tablename__="report"

    id = Column(Integer,primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resume_text = Column(Text)
    result = Column(Text)