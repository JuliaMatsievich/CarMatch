#!/usr/bin/env python3
"""
Script to remove interesting facts from car descriptions and keep only general information.
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def clean_car_descriptions(db_url):
    """
    Remove interesting facts from car descriptions and keep only general information
    """
    print("Cleaning car descriptions to remove interesting facts...")
    
    # Create database engine and session
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Get cars that have descriptions with interesting facts
        print("Fetching cars with enhanced descriptions...")
        result = db.execute(text("""
            SELECT id, description
            FROM cars
            WHERE description LIKE '%Интересные факты%'
        """))
        
        cars = result.fetchall()
        print(f"Found {len(cars)} cars with enhanced descriptions to clean")
        
        cleaned_count = 0
        for car in cars:
            car_id, full_description = car
            
            # Find the position of "Интересные факты:" and remove everything after it
            facts_pos = full_description.find("Интересные факты:")
            if facts_pos != -1:
                # Keep only the part before "Интересные факты:"
                cleaned_description = full_description[:facts_pos].strip()
                
                # Update the car record with cleaned description
                db.execute(
                    text("UPDATE cars SET description = :desc WHERE id = :car_id"),
                    {"desc": cleaned_description, "car_id": car_id}
                )
                
                cleaned_count += 1
                
                # Commit every 1000 updates
                if cleaned_count % 1000 == 0:
                    db.commit()
                    print(f"  Cleaned {cleaned_count} cars so far...")
        
        # Commit remaining changes
        db.commit()
        
        print(f"Cleaned {cleaned_count} cars by removing interesting facts")
        
        # Verify the updates
        result = db.execute(text("SELECT COUNT(*) FROM cars WHERE description LIKE '%Интересные факты%'"))
        cars_with_facts = result.fetchone()[0]
        print(f"Remaining cars with interesting facts: {cars_with_facts}")
        
        # Check how many cars have descriptions now
        result = db.execute(text("SELECT COUNT(*) FROM cars WHERE description IS NOT NULL"))
        cars_with_desc = result.fetchone()[0]
        print(f"Total cars with descriptions: {cars_with_desc}")
        
        # Show a sample of cleaned descriptions
        print("\nSample cleaned descriptions:")
        result = db.execute(text("""
            SELECT mark_name, model_name, year, description 
            FROM cars 
            WHERE description IS NOT NULL 
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
        # Rollback in case of error
        db.rollback()
        print(f"Error during description cleaning: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

def main():
    db_url = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
    
    print("Starting description cleaning process...")
    print(f"Using database: {db_url}")
    
    try:
        clean_car_descriptions(db_url)
        print("Description cleaning completed successfully!")
    except Exception as e:
        print(f"Error during description cleaning: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()