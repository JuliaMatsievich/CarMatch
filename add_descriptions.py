#!/usr/bin/env python3
"""
Script to add description field to cars table and populate it with model information.
"""

import sys
import os
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def add_description_field_and_populate(db_url):
    """
    Add description field to cars table and populate it with model information
    """
    print("Adding description field to cars table and populating it...")
    
    # Create database engine and session
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Add description column to cars table if it doesn't exist
        print("Adding description column to cars table...")
        try:
            db.execute(text("ALTER TABLE cars ADD COLUMN description TEXT"))
            print("Description column added successfully")
        except Exception as e:
            # If column already exists, continue
            print(f"Column may already exist: {str(e)}")
        
        # Commit the ALTER TABLE command
        db.commit()
        
        # Parse the XML file to extract model descriptions/information
        print("Parsing XML file to extract model information...")
        tree = ET.parse("cars.xml")
        root = tree.getroot()
        
        # Dictionary to store model descriptions for each brand-model combination
        model_descriptions = {}
        
        # Process each car brand (mark) in the catalog
        for mark_elem in root.findall('mark'):
            brand_name = mark_elem.get('name')
            
            # Process folders (models) under this brand
            for folder_elem in mark_elem.findall('folder'):
                model_name = folder_elem.get('name')
                
                # Look for model description or characteristics in the XML
                model_info_parts = []
                
                # Get model element if it exists
                model_elem = folder_elem.find('model')
                if model_elem is not None and model_elem.text:
                    model_info_parts.append(f"Модель: {model_elem.text}")
                
                # Look for any additional information in the folder
                # Check for generation descriptions
                generations = folder_elem.findall('generation')
                if generations:
                    # Take the first generation as representative
                    first_gen = generations[0]
                    if first_gen.text:
                        model_info_parts.append(f"Поколение: {first_gen.text}")
                
                # Look for modification characteristics
                modifications = folder_elem.findall('modification')
                if modifications:
                    # Take characteristics from the first modification as examples
                    first_mod = modifications[0]
                    tech_param_elem = first_mod.find('tech_param_id')
                    if tech_param_elem is not None and tech_param_elem.text:
                        model_info_parts.append(f"Технический параметр ID: {tech_param_elem.text}")
                
                # Create a description for this brand-model combination
                if model_info_parts:
                    description = ". ".join(model_info_parts) + "."
                else:
                    description = f"Автомобиль {brand_name} {model_name}."
                
                model_descriptions[(brand_name, model_name)] = description
        
        print(f"Collected descriptions for {len(model_descriptions)} brand-model combinations")
        
        # Update cars table with descriptions
        print("Updating cars table with descriptions...")
        
        # Create a temporary table with the descriptions
        db.execute(text("CREATE TEMP TABLE temp_descriptions AS SELECT DISTINCT mark_name, model_name FROM cars"))
        
        # Update the temp table with descriptions
        for (brand, model), desc in model_descriptions.items():
            try:
                db.execute(
                    text("UPDATE temp_descriptions SET description = :desc WHERE mark_name = :brand AND model_name = :model"),
                    {"desc": desc, "brand": brand, "model": model}
                )
            except:
                continue  # Skip if the brand/model combination doesn't exist in cars table
        
        # Update the main cars table using the temp table
        result = db.execute(text("""
            UPDATE cars 
            SET description = temp_descriptions.description
            FROM temp_descriptions
            WHERE cars.mark_name = temp_descriptions.mark_name
            AND cars.model_name = temp_descriptions.model_name
            AND cars.description IS NULL
        """))
        
        print(f"Updated {result.rowcount} cars with descriptions")
        
        # Drop the temporary table
        db.execute(text("DROP TABLE IF EXISTS temp_descriptions"))
        
        # Commit changes
        db.commit()
        
        # Verify the updates
        result = db.execute(text("SELECT COUNT(*) FROM cars WHERE description IS NOT NULL"))
        cars_with_desc = result.fetchone()[0]
        print(f"Total cars with description: {cars_with_desc}")
        
        if cars_with_desc > 0:
            # Show some sample records
            print("\nSample car records with descriptions:")
            result = db.execute(text("""
                SELECT id, mark_name, model_name, year, description 
                FROM cars 
                WHERE description IS NOT NULL 
                LIMIT 10
            """))
            samples = result.fetchall()
            for sample in samples:
                print(f"  ID: {sample[0]}, Brand: {sample[1]}, Model: {sample[2]}, Year: {sample[3]}")
                print(f"    Description: {sample[4][:100]}..." if len(sample[4]) > 100 else f"    Description: {sample[4]}")
                print()
        
    except Exception as e:
        # Rollback in case of error
        db.rollback()
        print(f"Error during description update: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

def main():
    db_url = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
    
    print("Starting description field addition and population process...")
    print(f"Using database: {db_url}")
    
    try:
        add_description_field_and_populate(db_url)
        print("Description field addition and population completed successfully!")
    except Exception as e:
        print(f"Error during description field addition: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()