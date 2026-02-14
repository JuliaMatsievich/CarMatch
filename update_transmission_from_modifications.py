#!/usr/bin/env python3
"""
Script to update the transmission field in the cars table with values from car_modifications.name field
"""

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def update_transmission_field(db_url):
    """
    Update the transmission field in the cars table with values from car_modifications.name
    """
    print("Updating transmission field in cars table from car_modifications.name...")

    # Create database engine and session
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Update the transmission field in cars table with values from car_modifications.name
        # Truncate to 30 characters to fit the column constraint
        result = db.execute(text("""
            UPDATE cars
            SET transmission = SUBSTRING(cm.name, 1, 30)
            FROM car_modifications cm
            WHERE cars.modification_id = cm.id
            AND (cars.transmission IS NULL OR cars.transmission = '');
        """))
        
        rows_updated = result.rowcount
        print(f"Updated {rows_updated} cars with transmission data from car_modifications.name")

        # Commit the changes
        db.commit()
        
        # Show some sample data to verify the update
        sample_result = db.execute(text("""
            SELECT c.id, c.mark_name, c.model_name, c.transmission, cm.name as modification_name
            FROM cars c
            JOIN car_modifications cm ON c.modification_id = cm.id
            WHERE c.transmission IS NOT NULL
            LIMIT 5;
        """))
        
        print("\nSample updated records:")
        print(f"{'Car ID':<8} {'Brand':<15} {'Model':<20} {'Transmission':<25} {'Mod Name':<30}")
        print("-" * 105)
        for row in sample_result:
            print(f"{row[0]:<8} {row[1]:<15} {row[2]:<20} {row[3]:<25} {row[4]:<30}")

    except Exception as e:
        # Rollback in case of error
        db.rollback()
        print(f"Error during transmission update: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

def main():
    db_url = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"

    print("Starting transmission field update process...")
    print(f"Using database: {db_url}")

    try:
        update_transmission_field(db_url)
        print("Transmission field update completed successfully!")
    except Exception as e:
        print(f"Error during transmission field update: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()