#!/usr/bin/env python3
"""
Script to populate the cars table based on the reference tables that already have year information.
"""

import sys
import os
import xml.etree.ElementTree as ET
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
        # First, let's update the car_generations table with year information from the XML
        print("Updating car_generations with year information from XML...")
        
        # Parse the XML file to extract year information
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
                            # Handle the Russian "н.в." which means "present day" or "current"
                            years_text = years_text.replace("н.в.", "present")
                            
                            # Split on the dash
                            parts = [part.strip() for part in years_text.split('-')]
                            
                            if len(parts) == 2:
                                start_year = parts[0]
                                end_year = parts[1]
                                years_data = {"start": start_year, "end": end_year}
                            elif len(parts) == 1:
                                years_data = {"single": parts[0]}
                            else:
                                continue
                            
                            # Store the year information for this generation
                            if gen_id not in gen_years_map:
                                gen_years_map[gen_id] = years_data
                            else:
                                # If we already have years for this gen, keep the first one we found
                                pass
        
        print(f"Found year information for {len(gen_years_map)} generations in XML")
        
        # Update car_generations table with year information
        updated_gens = 0
        for gen_ext_id, years_data in gen_years_map.items():
            try:
                # Convert external ID to integer for comparison
                gen_ext_id_int = int(gen_ext_id)
                
                result = db.execute(
                    text("""
                        UPDATE car_generations 
                        SET years = :years_data 
                        WHERE external_id = :gen_ext_id 
                        AND (years IS NULL OR years = '{}')
                    """),
                    {
                        "years_data": json.dumps(years_data),
                        "gen_ext_id": str(gen_ext_id_int)
                    }
                )
                
                if result.rowcount > 0:
                    updated_gens += 1
            except ValueError:
                # Skip if the external ID is not a valid integer
                continue
        
        print(f"Updated {updated_gens} generations with year information")
        
        # Now populate the cars table by joining the reference tables
        print("Populating cars table from reference tables...")
        
        # Get all modifications with their associated data
        result = db.execute(text("""
            SELECT 
                m.id as modification_id,
                m.name as modification_name,
                m.body_type,
                g.id as generation_id,
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
            WHERE NOT EXISTS (
                SELECT 1 FROM cars c 
                WHERE c.modification_id = m.id
            )
        """))
        
        modifications = result.fetchall()
        print(f"Found {len(modifications)} modifications to create cars for")
        
        # Insert car records for each modification
        inserted_cars = 0
        for mod in modifications:
            # Extract year from generation years JSON
            year_value = None
            if mod[5]:  # generation_years is not None
                try:
                    years_json = json.loads(mod[5])
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
                    "source_id": str(mod[0]),  # modification_id
                    "mark_name": mod[9],       # brand_name
                    "model_name": mod[7],      # model_name
                    "body_type": mod[2],       # body_type
                    "year": year_value,
                    "brand_id": mod[8],        # brand_id
                    "model_id": mod[6],        # model_id
                    "generation_id": mod[4],   # generation_id
                    "modification_id": mod[0]  # modification_id
                }
            )
            inserted_cars += 1
            
            # Commit every 1000 records to avoid memory issues
            if inserted_cars % 1000 == 0:
                db.commit()
                print(f"  Inserted {inserted_cars} cars so far...")
        
        # Commit remaining records
        db.commit()
        
        print(f"Successfully populated {inserted_cars} cars in the database!")
        
        # Verify the data
        result = db.execute(text("SELECT COUNT(*) FROM cars"))
        total_cars = result.fetchone()[0]
        print(f"Total cars in database now: {total_cars}")
        
        result = db.execute(text("SELECT COUNT(*) FROM cars WHERE year IS NOT NULL"))
        cars_with_year = result.fetchone()[0]
        print(f"Cars with year data: {cars_with_year}")
        
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