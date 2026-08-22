from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL.startswith("mysql+mysqldb://"):
    DATABASE_URL = DATABASE_URL.replace(
        "mysql+mysqldb://",
        "mysql+pymysql://",
        1
    )

engine_options = {"pool_pre_ping": True}

if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {
        "check_same_thread": False
    }

elif DATABASE_URL.startswith("mysql"):
    engine_options["connect_args"] = {
        "ssl": {
            "ca": "ca.pem",
            "check_hostname": True
        }
    }

engine = create_engine(DATABASE_URL, **engine_options)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()