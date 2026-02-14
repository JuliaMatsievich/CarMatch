#!/usr/bin/env python3
"""
Script to populate the description field in cars table with model information.
"""

import sys
import os
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def populate_descriptions(db_url):
    """
    Populate the description field in cars table with model information
    """
    print("Populating description field in cars table...")
    
    # Create database engine and session
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
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
                    # Look for body type
                    body_type_elem = first_mod.find('body_type')
                    if body_type_elem is not None and body_type_elem.text:
                        model_info_parts.append(f"Тип кузова: {body_type_elem.text}")
                    
                    # Look for years
                    years_elem = first_mod.find('years')
                    if years_elem is not None and years_elem.text:
                        model_info_parts.append(f"Годы выпуска: {years_elem.text}")
                
                # Create a description for this brand-model combination
                if model_info_parts:
                    description = ". ".join(model_info_parts) + "."
                else:
                    description = f"Автомобиль {brand_name} {model_name}."
                
                model_descriptions[(brand_name, model_name)] = description
        
        print(f"Collected descriptions for {len(model_descriptions)} brand-model combinations")
        
        # Update cars table with descriptions using individual updates
        print("Updating cars table with descriptions...")
        
        updated_count = 0
        for (brand, model), desc in model_descriptions.items():
            try:
                result = db.execute(
                    text("""
                        UPDATE cars 
                        SET description = :desc
                        WHERE mark_name = :brand 
                        AND model_name = :model
                        AND description IS NULL
                        """),
                    {"desc": desc, "brand": brand, "model": model}
                )
                updated_count += result.rowcount
                
                # Commit every 1000 updates to avoid memory issues
                if updated_count % 1000 == 0:
                    db.commit()
                    print(f"  Updated {updated_count} cars so far...")
                    
            except Exception as e:
                # Continue if there's an error with this particular update
                print(f"Error updating {brand} {model}: {str(e)}")
                continue
        
        # Commit remaining changes
        db.commit()
        
        print(f"Updated {updated_count} cars with descriptions")
        
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
    
    print("Starting description population process...")
    print(f"Using database: {db_url}")
    
    try:
        populate_descriptions(db_url)
        print("Description population completed successfully!")
    except Exception as e:
        print(f"Error during description population: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()