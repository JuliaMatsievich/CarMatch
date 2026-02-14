#!/usr/bin/env python3
"""
Script to verify that the transmission field in the cars table was updated correctly
with values from car_modifications.name field
"""

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def verify_transmission_update(db_url):
    """
    Verify that the transmission field in the cars table was updated correctly
    """
    print("Verifying transmission field updates...")

    # Create database engine and session
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Count how many cars have transmission data now
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM cars 
            WHERE transmission IS NOT NULL AND transmission != '';
        """))
        cars_with_transmission = result.fetchone()[0]
        
        print(f"Total cars with transmission data: {cars_with_transmission}")

        # Count total cars
        result = db.execute(text("SELECT COUNT(*) FROM cars;"))
        total_cars = result.fetchone()[0]
        
        print(f"Total cars in database: {total_cars}")

        # Sample records to verify the data
        sample_result = db.execute(text("""
            SELECT c.id, c.mark_name, c.model_name, c.transmission, cm.name as modification_name
            FROM cars c
            JOIN car_modifications cm ON c.modification_id = cm.id
            WHERE c.transmission IS NOT NULL AND c.transmission != ''
            LIMIT 10;
        """))
        
        print("\nSample records with updated transmission data:")
        print(f"{'Car ID':<8} {'Brand':<15} {'Model':<20} {'Transmission':<30} {'Mod Name':<30}")
        print("-" * 105)
        for row in sample_result:
            print(f"{row[0]:<8} {row[1]:<15} {row[2]:<20} {row[3]:<30} {row[4]:<30}")
            
        # Check if there are any cars still without transmission data
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM cars 
            WHERE transmission IS NULL OR transmission = '';
        """))
        cars_without_transmission = result.fetchone()[0]
        
        print(f"\nCars still without transmission data: {cars_without_transmission}")
        
        if cars_without_transmission == 0:
            print("[OK] All cars have been updated with transmission data!")
        else:
            print(f"[WARN] {cars_without_transmission} cars still don't have transmission data.")
            
        # Check if the transmission field matches the modification name (first 30 chars)
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM cars c
            JOIN car_modifications cm ON c.modification_id = cm.id
            WHERE c.transmission = SUBSTRING(cm.name, 1, 30);
        """))
        matching_records = result.fetchone()[0]
        
        print(f"Records where transmission matches first 30 chars of modification name: {matching_records}")
        
        if matching_records == total_cars:
            print("[OK] All transmission values match the corresponding modification names (truncated to 30 chars)!")
        else:
            print(f"[WARN] Not all transmission values match modification names.")

    except Exception as e:
        print(f"Error during verification: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

def main():
    db_url = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"

    print("Starting verification process...")
    print(f"Using database: {db_url}")

    try:
        verify_transmission_update(db_url)
        print("Verification completed successfully!")
    except Exception as e:
        print(f"Error during verification: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()