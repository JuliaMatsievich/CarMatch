import os
from sqlalchemy import create_engine, text

# Use the local database URL (since we're connecting from outside Docker)
DATABASE_URL = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

try:
    with engine.connect() as connection:
        print("Connected to PostgreSQL database!")
        
        # Check how many cars have descriptions with facts (should be 0 now)
        result = connection.execute(text("SELECT COUNT(*) FROM cars WHERE description LIKE '%Интересные факты%'"))
        cars_with_facts = result.fetchone()[0]
        print(f"Cars with interesting facts: {cars_with_facts} (should be 0)")
        
        # Check total cars with descriptions
        result = connection.execute(text("SELECT COUNT(*) FROM cars WHERE description IS NOT NULL"))
        cars_with_desc = result.fetchone()[0]
        print(f"Total cars with descriptions: {cars_with_desc}")
        
        # Show a sample of cleaned descriptions
        print("\nSample cleaned descriptions:")
        result = connection.execute(text("""
            SELECT mark_name, model_name, year, description 
            FROM cars 
            WHERE description IS NOT NULL 
            LIMIT 10
        """))
        samples = result.fetchall()
        for i, sample in enumerate(samples):
            print(f"  {i+1}. {sample[0]} {sample[1]} ({sample[2]}):")
            # Show full description
            print(f"     {sample[3]}")
            print()

except Exception as e:
    print(f"Database connection failed: {str(e)}")
    import traceback
    traceback.print_exc()