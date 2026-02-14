import os
from sqlalchemy import create_engine, text

# Use the local database URL (since we're connecting from outside Docker)
DATABASE_URL = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

try:
    with engine.connect() as connection:
        print("Connected to PostgreSQL database!")
        
        # Check the cars table structure
        result = connection.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'cars' AND column_name = 'description'
        """))
        desc_col = result.fetchone()
        if desc_col:
            print(f"Description column exists: {desc_col[0]} ({desc_col[1]})")
        else:
            print("Description column does not exist!")
        
        # Check how many cars have descriptions
        result = connection.execute(text("SELECT COUNT(*) FROM cars WHERE description IS NOT NULL"))
        cars_with_desc = result.fetchone()[0]
        print(f"Total cars with description: {cars_with_desc}")
        
        # Check total cars
        result = connection.execute(text("SELECT COUNT(*) FROM cars"))
        total_cars = result.fetchone()[0]
        print(f"Total cars in table: {total_cars}")
        
        # Show a sample of descriptions
        print("\nSample descriptions:")
        result = connection.execute(text("""
            SELECT mark_name, model_name, year, description 
            FROM cars 
            WHERE description IS NOT NULL 
            LIMIT 5
        """))
        samples = result.fetchall()
        for sample in samples:
            print(f"  {sample[0]} {sample[1]} ({sample[2]}): {sample[3][:100]}...")

except Exception as e:
    print(f"Database connection failed: {str(e)}")
    import traceback
    traceback.print_exc()