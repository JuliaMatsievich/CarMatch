#!/usr/bin/env python3
"""
Script to check the current schema of the cars table
"""

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def check_schema():
    db_url = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
    
    # Create database engine and session
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Query to get column information
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'cars' 
            ORDER BY ordinal_position
        """))
        
        print("Current schema of 'cars' table:")
        print("-" * 50)
        print(f"{'Column Name':<25} {'Data Type':<20} {'Nullable'}")
        print("-" * 50)
        
        for row in result:
            print(f"{row[0]:<25} {row[1]:<20} {row[2]}")
            
    except Exception as e:
        print(f"Error checking schema: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_schema()