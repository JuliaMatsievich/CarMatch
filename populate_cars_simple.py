#!/usr/bin/env python3
"""
Script to populate the cars table based on the reference tables that already have year information.
This version will focus on getting the data structure right first.
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

def populate_cars_from_references(db_url):
    """
    Populate the cars table by joining data from reference tables
    """
    print("Populating cars table from reference tables...")
    
    # Create database engine and session
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("Checking existing data in reference tables...")
        
        # Check how many records exist in each table
        tables = ['car_brands', 'car_models', 'car_generations', 'car_modifications', 'cars']
        for table in tables:
            result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.fetchone()[0]
            print(f"  {table}: {count} records")
        
        # Let's first try to insert just a few records to make sure the foreign key relationships are correct
        print("Inserting sample cars records...")
        
        # Get a few sample records from the reference tables
        result = db.execute(text("""
            SELECT 
                m.id as modification_id,
                m.name as modification_name,
                m.body_type,
                g.id as generation_id,
                g.external_id as generation_external_id,
                g.name as generation_name,
                g.years as generation_years,
                mo.id as model_id,
                mo.name as model_name,
                b.id as brand_id,
                b.name as brand_name
            FROM car_modifications m
            JOIN car_generations g ON m.generation_id = g.id
            JOIN car_models mo ON g.model_id = mo.id
            JOIN car_brands b ON mo.brand_id = b.id
            LIMIT 5
        """))
        
        modifications = result.fetchall()
        print(f"Retrieved {len(modifications)} sample modifications")
        
        for mod in modifications:
            print(f"  Mod ID: {mod[0]}, Brand: {mod[10]}, Model: {mod[8]}, Gen External ID: {mod[4]}, Gen Years: {mod[6]}")
        
        # Now insert these as car records
        inserted_cars = 0
        for mod in modifications:
            # Extract year from generation years JSON
            year_value = None
            if mod[6]:  # generation_years is not None
                try:
                    years_json = json.loads(mod[6])
                    if 'start' in years_json and years_json['start'].isdigit():
                        year_value = int(years_json['start'])
                    elif 'single' in years_json and years_json['single'].isdigit():
                        year_value = int(years_json['single'])
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Insert the car record
            db.execute(
                text("""
                    INSERT INTO cars (
                        source, source_id, mark_name, model_name, 
                        body_type, year, brand_id, model_id, 
                        generation_id, modification_id
                    ) VALUES (
                        :source, :source_id, :mark_name, :model_name,
                        :body_type, :year, :brand_id, :model_id,
                        :generation_id, :modification_id
                    )
                """),
                {
                    "source": "yandex",
                    "source_id": str(mod[4]),  # generation_external_id (the external ID from XML)
                    "mark_name": mod[10],      # brand_name
                    "model_name": mod[8],      # model_name
                    "body_type": mod[2],       # body_type
                    "year": year_value,
                    "brand_id": mod[9],        # brand_id
                    "model_id": mod[7],        # model_id
                    "generation_id": mod[3],   # generation_id (internal ID)
                    "modification_id": mod[0]  # modification_id (internal ID)
                }
            )
            inserted_cars += 1
        
        db.commit()
        print(f"Successfully inserted {inserted_cars} sample car records!")
        
        # Now let's do the bulk insert for all modifications
        print("Inserting all remaining car records...")
        
        # Count how many cars we already have
        result = db.execute(text("SELECT COUNT(*) FROM cars"))
        initial_count = result.fetchone()[0]
        print(f"Initial car count: {initial_count}")
        
        # Insert all modifications that don't already have a corresponding car record
        result = db.execute(text("""
            INSERT INTO cars (source, source_id, mark_name, model_name, body_type, year, brand_id, model_id, generation_id, modification_id)
            SELECT 
                'yandex' as source,
                g.external_id as source_id,  -- Use external_id as source_id
                b.name as mark_name,
                mo.name as model_name,
                m.body_type,
                CASE 
                    WHEN g.years IS NOT NULL AND g.years != '{}' THEN 
                        CASE 
                            WHEN (g.years->>'start') ~ '^[0-9]+$' 
                            THEN (g.years->>'start')::INTEGER
                            WHEN (g.years->>'single') ~ '^[0-9]+$' 
                            THEN (g.years->>'single')::INTEGER
                            ELSE NULL
                        END
                    ELSE NULL
                END as year,
                b.id as brand_id,
                mo.id as model_id,
                g.id as generation_id,  -- Use internal ID for foreign key
                m.id as modification_id  -- Use internal ID for foreign key
            FROM car_modifications m
            JOIN car_generations g ON m.generation_id = g.id
            JOIN car_models mo ON g.model_id = mo.id
            JOIN car_brands b ON mo.brand_id = b.id
            WHERE NOT EXISTS (
                SELECT 1 FROM cars c 
                WHERE c.modification_id = m.id
            )
        """))
        
        db.commit()
        print(f"Inserted additional cars via bulk query")
        
        # Final count
        result = db.execute(text("SELECT COUNT(*) FROM cars"))
        final_count = result.fetchone()[0]
        print(f"Final car count: {final_count}")
        
        result = db.execute(text("SELECT COUNT(*) FROM cars WHERE year IS NOT NULL"))
        cars_with_year = result.fetchone()[0]
        print(f"Cars with year data: {cars_with_year}")
        
        # Show some sample records
        print("\nSample car records with year data:")
        result = db.execute(text("""
            SELECT id, mark_name, model_name, year, body_type 
            FROM cars 
            WHERE year IS NOT NULL 
            LIMIT 10
        """))
        samples = result.fetchall()
        for sample in samples:
            print(f"  ID: {sample[0]}, Brand: {sample[1]}, Model: {sample[2]}, Year: {sample[3]}, Body: {sample[4]}")

    except Exception as e:
        # Rollback in case of error
        db.rollback()
        print(f"Error during data population: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

def main():
    db_url = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
    
    print("Starting car data population process...")
    print(f"Using database: {db_url}")
    
    try:
        populate_cars_from_references(db_url)
        print("Data population completed successfully!")
    except Exception as e:
        print(f"Error during data population: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()