#!/usr/bin/env python3
"""
Script to load car data from XML file into the database, including year information.
"""

import sys
import os
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
import re

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

def load_cars_from_xml(xml_file_path, db_url):
    """
    Load car data from XML file into the database
    """
    print(f"Loading data from XML file: {xml_file_path}")
    
    # Create database engine and session
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Parse the XML file
        print("Parsing XML file...")
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Dictionary to map external IDs to our internal IDs
        brand_id_map = {}
        model_id_map = {}
        generation_id_map = {}
        
        # First, populate the mapping dictionaries from existing database records
        print("Loading existing database mappings...")
        
        # Get existing brand mappings
        result = db.execute(text("SELECT id, name FROM car_brands"))
        for row in result:
            brand_id_map[row[1]] = row[0]  # row[1] is name, row[0] is id
        
        # Get existing model mappings
        result = db.execute(text("SELECT id, external_id FROM car_models"))
        for row in result:
            model_id_map[row[1]] = row[0]  # row[1] is external_id, row[0] is id
        
        # Get existing generation mappings
        result = db.execute(text("SELECT id, external_id FROM car_generations"))
        for row in result:
            generation_id_map[row[1]] = row[0]  # row[1] is external_id, row[0] is id
        
        print(f"Loaded {len(brand_id_map)} brands, {len(model_id_map)} models, {len(generation_id_map)} generations from DB")
        
        # Process each car brand (mark) in the catalog
        processed_brands = 0
        processed_models = 0
        processed_generations = 0
        processed_modifications = 0
        processed_cars = 0
        
        print("Processing XML data...")
        
        for idx, mark_elem in enumerate(root.findall('mark')):
            mark_name = mark_elem.get('name')
            code_elem = mark_elem.find('code')
            code = code_elem.text if code_elem is not None else None

            print(f"Processing brand {idx+1}: {mark_name}")

            # Get brand ID from our mapping
            if mark_name not in brand_id_map:
                print(f"  Brand {mark_name} not found in database mapping!")
                continue
            
            brand_id = brand_id_map[mark_name]

            # Process folders (models) under this brand
            for folder_elem in mark_elem.findall('folder'):
                folder_name = folder_elem.get('name')
                folder_id = folder_elem.get('id')

                # Get model ID from our mapping
                if folder_id not in model_id_map:
                    print(f"    Model with external_id {folder_id} not found in database mapping!")
                    continue
                
                model_id = model_id_map[folder_id]

                # Process generations
                for gen_elem in folder_elem.findall('generation'):
                    gen_id = gen_elem.get('id')
                    gen_text = gen_elem.text

                    # Get generation ID from our mapping
                    if gen_id not in generation_id_map:
                        print(f"      Generation with external_id {gen_id} not found in database mapping!")
                        continue
                    
                    generation_id = generation_id_map[gen_id]

                    # Process modifications under this folder
                    for mod_elem in folder_elem.findall('modification'):
                        mod_name = mod_elem.get('name')
                        mod_id = mod_elem.get('id')

                        # Extract additional fields from modification
                        body_type_elem = mod_elem.find('body_type')
                        body_type = body_type_elem.text if body_type_elem is not None else None

                        years_elem = mod_elem.find('years')
                        years_text = years_elem.text if years_elem is not None else None
                        
                        # Parse years range if available
                        years_data = parse_years_text(years_text)
                        
                        # Update the car_generations table with years data if it's not already set
                        if years_data:
                            result = db.execute(
                                text("""
                                    UPDATE car_generations 
                                    SET years = :years_data 
                                    WHERE id = :generation_id 
                                    AND (years IS NULL OR years = '{}' OR years = '')
                                """),
                                {
                                    "years_data": json.dumps(years_data),
                                    "generation_id": generation_id
                                }
                            )
                            
                            if result.rowcount > 0:
                                print(f"        Updated generation {generation_id} with years: {years_data}")
                                processed_generations += 1
                        
                        # Now create or update the main cars table entry
                        # First, try to find if a car with this combination already exists
                        result = db.execute(
                            text("""
                                SELECT id FROM cars 
                                WHERE mark_name = :mark_name 
                                AND model_name = :model_name 
                                AND modification_id = :modification_id
                                LIMIT 1
                            """),
                            {
                                "mark_name": mark_name,
                                "model_name": folder_name,
                                "modification_id": mod_id
                            }
                        )
                        
                        existing_car = result.fetchone()
                        
                        if existing_car:
                            # Update the existing car with year information if not present
                            year_value = None
                            if 'start' in years_data and years_data['start'].isdigit():
                                year_value = int(years_data['start'])
                            
                            if year_value:
                                db.execute(
                                    text("""
                                        UPDATE cars 
                                        SET year = :year 
                                        WHERE id = :car_id 
                                        AND year IS NULL
                                    """),
                                    {
                                        "year": year_value,
                                        "car_id": existing_car[0]
                                    }
                                )
                        else:
                            # Insert a new car record
                            year_value = None
                            if 'start' in years_data and years_data['start'].isdigit():
                                year_value = int(years_data['start'])
                            
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
                                    "source_id": mod_id,
                                    "mark_name": mark_name,
                                    "model_name": folder_name,
                                    "body_type": body_type,
                                    "year": year_value,
                                    "brand_id": brand_id,
                                    "model_id": model_id,
                                    "generation_id": generation_id,
                                    "modification_id": mod_id
                                }
                            )
                            processed_cars += 1

        # Commit all changes to the database
        db.commit()
        print(f"Data loading completed successfully!")
        print(f"Updated {processed_generations} generations with year data")
        print(f"Added {processed_cars} new cars to the database")

    except Exception as e:
        # Rollback in case of error
        db.rollback()
        print(f"Error during data loading: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

def main():
    xml_file_path = "cars.xml"
    db_url = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
    
    print("Starting car data loading process...")
    print(f"Using XML file: {xml_file_path}")
    print(f"Using database: {db_url}")
    
    try:
        load_cars_from_xml(xml_file_path, db_url)
        print("Data loading completed successfully!")
    except Exception as e:
        print(f"Error during data loading: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()