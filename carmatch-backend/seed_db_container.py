#!/usr/bin/env python3
"""
Script to seed the database with car reference data from XML file.
This version is designed to run inside the Docker container.
"""

import sys
import os

# Add the src directory to the path so we can import modules
sys.path.insert(0, '/app/src')

import xml.etree.ElementTree as ET
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import CarBrand, CarModel, CarGeneration, CarModification, CarComplectation
from src.config import settings


def parse_xml_and_seed_database(xml_file_path: str):
    """
    Parse the cars.xml file and seed the database with normalized reference data.
    """
    print(f"Parsing XML file: {xml_file_path}")
    
    # Parse the XML file
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    # Create database engine and session
    engine = create_engine(settings.get_database_url(), pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Process each car brand (mark) in the catalog
        for idx, mark_elem in enumerate(root.findall('mark')):
            mark_name = mark_elem.get('name')
            code_elem = mark_elem.find('code')
            code = code_elem.text if code_elem is not None else None
            
            print(f"Processing brand {idx+1}: {mark_name}")
            
            # Check if brand already exists
            brand = db.query(CarBrand).filter(CarBrand.name == mark_name).first()
            if not brand:
                brand = CarBrand(name=mark_name, code=code)
                db.add(brand)
                db.flush()  # Get the ID without committing
            else:
                print(f"  Brand {mark_name} already exists, skipping creation")
            
            # Process folders (models) under this brand
            for folder_elem in mark_elem.findall('folder'):
                folder_name = folder_elem.get('name')
                folder_id = folder_elem.get('id')
                
                # Check if model already exists for this brand
                model = db.query(CarModel).filter(
                    CarModel.brand_id == brand.id,
                    CarModel.name == folder_name
                ).first()
                
                if not model:
                    model = CarModel(
                        brand_id=brand.id,
                        name=folder_name,
                        external_id=folder_id
                    )
                    db.add(model)
                    db.flush()  # Get the ID without committing
                else:
                    print(f"    Model {folder_name} already exists for brand {mark_name}, skipping creation")
                
                # Process model name (if present as a separate element)
                model_elem = folder_elem.find('model')
                if model_elem is not None:
                    # The model name is already captured as folder name
                    pass
                
                # Process generations
                for gen_elem in folder_elem.findall('generation'):
                    gen_id = gen_elem.get('id')
                    gen_text = gen_elem.text
                    
                    # Check if generation already exists for this model
                    generation = db.query(CarGeneration).filter(
                        CarGeneration.model_id == model.id,
                        CarGeneration.external_id == gen_id
                    ).first()
                    
                    if not generation:
                        generation = CarGeneration(
                            model_id=model.id,
                            name=gen_text,
                            external_id=gen_id,
                            years={}  # Will be populated later if needed
                        )
                        db.add(generation)
                        db.flush()  # Get the ID without committing
                    else:
                        print(f"      Generation {gen_text} already exists for model {folder_name}, skipping creation")
                
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
                    years_data = {}
                    if years_text:
                        # Example: "2019 - 2021" or "2019 - н.в." (present day)
                        parts = years_text.split(' - ')
                        if len(parts) == 2:
                            years_data = {
                                'start': parts[0],
                                'end': parts[1]
                            }
                        else:
                            years_data = {
                                'single': years_text
                            }
                    
                    # Check if modification already exists
                    modification = db.query(CarModification).filter(
                        CarModification.generation_id == generation.id,
                        CarModification.external_id == mod_id
                    ).first()
                    
                    if not modification:
                        modification = CarModification(
                            generation_id=generation.id,
                            name=mod_name,
                            external_id=mod_id,
                            body_type=body_type
                        )
                        db.add(modification)
                        db.flush()  # Get the ID without committing
                    else:
                        print(f"      Modification {mod_name} already exists for generation {gen_text}, skipping creation")
                    
                    # Process complectations under this modification
                    complectations_elem = mod_elem.find('complectations')
                    if complectations_elem is not None:
                        for comp_elem in complectations_elem.findall('complectation'):
                            comp_name = comp_elem.text
                            comp_id = comp_elem.get('id')
                            
                            # Check if complectation already exists
                            complectation = db.query(CarComplectation).filter(
                                CarComplectation.modification_id == modification.id,
                                CarComplectation.external_id == comp_id
                            ).first()
                            
                            if not complectation:
                                complectation = CarComplectation(
                                    modification_id=modification.id,
                                    name=comp_name,
                                    external_id=comp_id
                                )
                                db.add(complectation)
                            else:
                                print(f"        Complectation {comp_name} already exists for modification {mod_name}, skipping creation")
        
        # Commit all changes to the database
        db.commit()
        print("Database seeding completed successfully!")
        
    except Exception as e:
        # Rollback in case of error
        db.rollback()
        print(f"Error during seeding: {str(e)}")
        raise e
    finally:
        db.close()


def main():
    """
    Main function to run the seeder.
    """
    xml_file_path = "/tmp/cars.xml"  # Path inside the container
    
    print("Starting database seeding process...")
    print(f"Using XML file: {xml_file_path}")
    
    try:
        parse_xml_and_seed_database(xml_file_path)
        print("Seeding completed successfully!")
    except FileNotFoundError:
        print(f"Error: XML file not found at {xml_file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during seeding: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()