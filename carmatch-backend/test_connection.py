import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from sqlalchemy import create_engine, text
from src.config import settings

def test_connection():
    try:
        print("Testing database connection...")
        print(f"Database URL: {settings.get_database_url()}")
        
        engine = create_engine(settings.get_database_url(), pool_pre_ping=True)
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Connection successful!")
            print(f"Query result: {result.fetchone()}")
            return True
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()