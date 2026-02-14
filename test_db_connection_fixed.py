import subprocess
import sys
import os

def test_db_connection():
    print("Testing database connection from a Python container...")
    
    # Create a simple Python script to test DB connection
    test_script = '''
import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://carmatch:carmatch@postgres:5432/carmatch"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print(f"Connected to PostgreSQL: {version[:50]}...")
        print("Database connection successful!")
        
        # Check if our reference tables exist
        result = connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'car_%';"))
        tables = [row[0] for row in result.fetchall()]
        print(f"Reference data tables found: {tables}")
        
        # Count records in each table
        for table in tables:
            count_result = connection.execute(text(f"SELECT COUNT(*) FROM {table};"))
            count = count_result.fetchone()[0]
            print(f"  {table}: {count} records")
        
except Exception as e:
    print(f"Database connection failed: {str(e)}")
    import traceback
    traceback.print_exc()
'''
    
    # Write the test script to a temporary file
    with open("test_db_connection.py", "w") as f:
        f.write(test_script)
    
    try:
        # Run the test in a Python container connected to the PostgreSQL network
        cmd = [
            "docker", "run", "--rm",
            "--network", "container:carmatch-postgres",
            "-v", f"{os.getcwd()}:/app",
            "python:3.10-slim",
            "sh", "-c", 
            "pip install --no-cache-dir sqlalchemy psycopg[binary] && python /app/test_db_connection.py"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    finally:
        # Clean up
        if os.path.exists("test_db_connection.py"):
            os.remove("test_db_connection.py")

if __name__ == "__main__":
    success = test_db_connection()
    if success:
        print("\n[SUCCESS] Database connection test passed!")
    else:
        print("\n[ERROR] Database connection test failed!")