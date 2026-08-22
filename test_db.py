from sqlalchemy import text
from db import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Database connected successfully!")
        print("Result:", result.fetchone())

except Exception as e:
    print("Database connection failed!")
    print(e)