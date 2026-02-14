#!/usr/bin/env python3
"""
Script to update the car_generations table with year information from the XML file,
and then update the cars table with year data.
"""

import sys
import os
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

def parse_years_text(years_text):
    """
    Parse years text like "2019 - 2021" or "2019 - н.в." and return a dict
    """
    if not years_text:
        return {}
    
    # Handle the Russian "н.в." which means "present day" or "current"
    years_text = years_text.replace("н.в.", "present")
    
    # Split on the dash
    parts = [part.strip() for part in years_text.split('-')]
    
    if len(parts) == 2:
        start_year = parts[0]
        end_year = parts[1]
        return {
            "start": start_year,
            "end": end_year
        }
    elif len(parts) == 1:
        return {
            "single": parts[0]
        }
    else:
        return {}

def update_generation_years(db_url):
    """
    Update the car_generations table with year information from the XML file
    """
    print("Updating car_generations with year information from XML...")
    
    # Create database engine and session
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Parse the XML file to extract year information
        print("Parsing XML file...")
        tree = ET.parse("cars.xml")
        root = tree.getroot()
        
        # Dictionary to store year information for each generation ID
        gen_years_map = {}
        
        # Process each car brand (mark) in the catalog
        for mark_elem in root.findall('mark'):
            # Process folders (models) under this brand
            for folder_elem in mark_elem.findall('folder'):
                # Process generations
                for gen_elem in folder_elem.findall('generation'):
                    gen_id = gen_elem.get('id')
                    
                    # Process modifications under this folder to get year info
                    for mod_elem in folder_elem.findall('modification'):
                        years_elem = mod_elem.find('years')
                        if years_elem is not None and years_elem.text:
                            years_text = years_elem.text
                            years_data = parse_years_text(years_text)
                            
                            # Store the year information for this generation if not already stored
                            if gen_id not in gen_years_map:
                                gen_years_map[gen_id] = years_data
        
        print(f"Found year information for {len(gen_years_map)} generations in XML")
        
        # Update car_generations table with year information
        updated_gens = 0
        for gen_ext_id, years_data in gen_years_map.items():
            try:
                # Update only if years is currently empty/null
                result = db.execute(
                    text("""
                        UPDATE car_generations 
                        SET years = :years_data 
                        WHERE external_id = :gen_ext_id 
                        AND (years IS NULL OR years = '{}')
                    """),
                    {
                        "years_data": json.dumps(years_data),
                        "gen_ext_id": str(gen_ext_id)
                    }
                )
                
                if result.rowcount > 0:
                    updated_gens += 1
            except Exception as e:
                # Skip if there's an error with this particular ID
                print(f"Error updating generation {gen_ext_id}: {str(e)}")
                continue
        
        print(f"Updated {updated_gens} generations with year information")
        
        # Now update the cars table with year information based on updated generation data
        print("Updating cars table with year information...")
        
        result = db.execute(text("""
            UPDATE cars 
            SET year = (
                CASE 
                    WHEN cg.years IS NOT NULL AND cg.years != '{}' THEN 
                        CASE 
                            WHEN (cg.years->>'start') ~ '^[0-9]+$' 
                            THEN (cg.years->>'start')::INTEGER
                            WHEN (cg.years->>'single') ~ '^[0-9]+$' 
                            THEN (cg.years->>'single')::INTEGER
                            ELSE NULL
                        END
                    ELSE NULL
                END
            )
            FROM car_generations cg
            WHERE cars.generation_id = cg.id
            AND cars.year IS NULL
        """))
        
        print(f"Updated {result.rowcount} cars with year information")
        
        # Commit changes
        db.commit()
        
        # Verify the updates
        result = db.execute(text("SELECT COUNT(*) FROM cars WHERE year IS NOT NULL"))
        cars_with_year = result.fetchone()[0]
        print(f"Total cars with year data: {cars_with_year}")
        
        if cars_with_year > 0:
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
        print(f"Error during data update: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

def main():
    db_url = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
    
    print("Starting generation year update process...")
    print(f"Using database: {db_url}")
    
    try:
        update_generation_years(db_url)
        print("Generation year update completed successfully!")
    except Exception as e:
        print(f"Error during generation year update: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()