import os
from sqlalchemy import create_engine, text

# Use the local database URL (since we're connecting from outside Docker)
DATABASE_URL = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

try:
    with engine.connect() as connection:
        print("Connected to PostgreSQL database!")
        
        # Check how many cars have enhanced descriptions with facts
        result = connection.execute(text("SELECT COUNT(*) FROM cars WHERE description LIKE '%Интересные факты%'"))
        cars_with_facts = result.fetchone()[0]
        print(f"Total cars with enhanced descriptions containing facts: {cars_with_facts}")
        
        # Check total cars
        result = connection.execute(text("SELECT COUNT(*) FROM cars"))
        total_cars = result.fetchone()[0]
        print(f"Total cars in table: {total_cars}")
        
        # Show a sample of enhanced descriptions
        print("\nSample enhanced descriptions:")
        result = connection.execute(text("""
            SELECT mark_name, model_name, year, description 
            FROM cars 
            WHERE description LIKE '%Интересные факты%' 
            LIMIT 5
        """))
        samples = result.fetchall()
        for i, sample in enumerate(samples):
            print(f"  {i+1}. {sample[0]} {sample[1]} ({sample[2]}):")
            # Show first 200 characters of description
            desc_preview = sample[3][:200] + "..." if len(sample[3]) > 200 else sample[3]
            print(f"     {desc_preview}")
            print()

except Exception as e:
    print(f"Database connection failed: {str(e)}")
    import traceback
    traceback.print_exc()