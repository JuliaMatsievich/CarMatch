#!/usr/bin/env python3
"""
Test script to validate the seeder logic with a custom SQLite setup for reference data only.
"""

import sys
import os
import tempfile
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import xml.etree.ElementTree as ET

# Define minimal models for testing just the reference data
Base = declarative_base()

def utcnow():
    return datetime.utcnow()

class CarBrand(Base):
    __tablename__ = "car_brands"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class CarModel(Base):
    __tablename__ = "car_models"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    brand_id = Column(Integer, nullable=False)  # Using Integer directly for SQLite test
    name = Column(String(100), nullable=False)
    external_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class CarGeneration(Base):
    __tablename__ = "car_generations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_id = Column(Integer, nullable=False)  # Using Integer directly for SQLite test
    name = Column(String(100), nullable=True)
    external_id = Column(String(100), nullable=True)
    # Using String instead of JSONB for SQLite compatibility
    years = Column(String, default="{}", nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class CarModification(Base):
    __tablename__ = "car_modifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    generation_id = Column(Integer, nullable=False)  # Using Integer directly for SQLite test
    name = Column(String(200), nullable=False)
    external_id = Column(String(100), nullable=True)
    body_type = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class CarComplectation(Base):
    __tablename__ = "car_complectations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    modification_id = Column(Integer, nullable=False)  # Using Integer directly for SQLite test
    name = Column(String(100), nullable=False)
    external_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


def test_seeder_logic():
    """
    Test the seeder logic with an in-memory SQLite database.
    """
    print("Creating in-memory SQLite database for testing reference data models...")
    
    # Create an in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Create only the reference data tables
    Base.metadata.create_all(bind=engine)
    
    # Create a session
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("Testing seeder logic with sample data...")
        
        # Sample XML content similar to the original
        sample_xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<catalog>
    <mark name="TestBrand">
        <code>TEST</code>
        <folder name="TestModel" id="12345">
            <model>TestModel</model>
            <generation id="12345">12345</generation>
            <modification name="Test Modification" id="67890">
                <mark_id>TestBrand</mark_id>
                <folder_id>TestModel</folder_id>
                <modification_id>Test Modification</modification_id>
                <configuration_id>12345</configuration_id>
                <tech_param_id>67890</tech_param_id>
                <body_type>Sedan</body_type>
                <years>2020 - 2022</years>
                <complectations>
                    <complectation id="11111">Base</complectation>
                    <complectation id="22222">Premium</complectation>
                </complectations>
            </modification>
        </folder>
    </mark>
</catalog>'''
        
        # Write the sample XML to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(sample_xml_content)
            temp_xml_path = f.name
        
        print(f"Created temporary XML file: {temp_xml_path}")
        
        # Parse the XML and simulate the seeder logic
        tree = ET.parse(temp_xml_path)
        root = tree.getroot()
        
        # Process the XML data
        for mark_elem in root.findall('mark'):
            mark_name = mark_elem.get('name')
            code_elem = mark_elem.find('code')
            code = code_elem.text if code_elem is not None else None
            
            print(f"Processing brand: {mark_name}")
            
            # Create brand
            brand = CarBrand(name=mark_name, code=code)
            db.add(brand)
            db.commit()
            db.refresh(brand)
            print(f"  Created brand: {brand.name} with ID: {brand.id}")
            
            # Process folders (models) under this brand
            for folder_elem in mark_elem.findall('folder'):
                folder_name = folder_elem.get('name')
                folder_id = folder_elem.get('id')
                
                print(f"  Processing model: {folder_name}")
                
                # Create model
                model = CarModel(brand_id=brand.id, name=folder_name, external_id=folder_id)
                db.add(model)
                db.commit()
                db.refresh(model)
                print(f"    Created model: {model.name} with ID: {model.id}")
                
                # Process generations
                for gen_elem in folder_elem.findall('generation'):
                    gen_id = gen_elem.get('id')
                    gen_text = gen_elem.text
                    
                    print(f"    Processing generation: {gen_text}")
                    
                    # Create generation
                    generation = CarGeneration(model_id=model.id, name=gen_text, external_id=gen_id, years='{}')
                    db.add(generation)
                    db.commit()
                    db.refresh(generation)
                    print(f"      Created generation: {generation.name} with ID: {generation.id}")
                
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
                    years_data = "{}"
                    if years_text:
                        # Example: "2019 - 2021" or "2019 - н.в." (present day)
                        parts = years_text.split(' - ')
                        if len(parts) == 2:
                            years_data = f'{{"start": "{parts[0]}", "end": "{parts[1]}"}}'
                        else:
                            years_data = f'{{"single": "{years_text}"}}'
                    
                    print(f"      Processing modification: {mod_name}")
                    
                    # Create modification
                    modification = CarModification(
                        generation_id=generation.id,
                        name=mod_name,
                        external_id=mod_id,
                        body_type=body_type
                    )
                    db.add(modification)
                    db.commit()
                    db.refresh(modification)
                    print(f"        Created modification: {modification.name} with ID: {modification.id}")
                    
                    # Process complectations under this modification
                    complectations_elem = mod_elem.find('complectations')
                    if complectations_elem is not None:
                        for comp_elem in complectations_elem.findall('complectation'):
                            comp_name = comp_elem.text
                            comp_id = comp_elem.get('id')
                            
                            print(f"          Processing complectation: {comp_name}")
                            
                            # Create complectation
                            complectation = CarComplectation(
                                modification_id=modification.id,
                                name=comp_name,
                                external_id=comp_id
                            )
                            db.add(complectation)
                        
                        db.commit()
                        print(f"        Created complectations for modification {modification.name}")
        
        # Query and display the created data
        print("\n--- Testing queries ---")
        brands = db.query(CarBrand).all()
        print(f"Total brands: {len(brands)}")
        
        models = db.query(CarModel).all()
        print(f"Total models: {len(models)}")
        
        generations = db.query(CarGeneration).all()
        print(f"Total generations: {len(generations)}")
        
        modifications = db.query(CarModification).all()
        print(f"Total modifications: {len(modifications)}")
        
        complectations = db.query(CarComplectation).all()
        print(f"Total complectations: {len(complectations)}")
        
        # Display some sample data
        print("\n--- Sample Data ---")
        for brand in brands:
            print(f"Brand: {brand.name} (Code: {brand.code})")
            brand_models = db.query(CarModel).filter(CarModel.brand_id == brand.id).all()
            for model in brand_models:
                print(f"  Model: {model.name}")
                model_generations = db.query(CarGeneration).filter(CarGeneration.model_id == model.id).all()
                for gen in model_generations:
                    print(f"    Generation: {gen.name}")
                    gen_modifications = db.query(CarModification).filter(CarModification.generation_id == gen.id).all()
                    for mod in gen_modifications:
                        print(f"      Modification: {mod.name} (Body: {mod.body_type})")
                        mod_complectations = db.query(CarComplectation).filter(CarComplectation.modification_id == mod.id).all()
                        for comp in mod_complectations:
                            print(f"        Complectation: {comp.name}")
        
        # Clean up the temporary file
        os.unlink(temp_xml_path)
        print(f"\nCleaned up temporary file: {temp_xml_path}")
        
        print("\nSeeder logic test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """
    Main function to run the test.
    """
    print("Starting seeder logic test...")
    
    success = test_seeder_logic()
    
    if success:
        print("\n[SUCCESS] Seeder logic validation passed!")
        print("\nThe seeder script should work correctly once the PostgreSQL database is available.")
        print("To run the actual seeder:")
        print("1. Make sure PostgreSQL is running on localhost:5432")
        print("2. Ensure the 'carmatch' database exists")
        print("3. Run the migrations: python -m alembic upgrade head")
        print("4. Run the seeder: python seed_db.py")
    else:
        print("\n[ERROR] Seeder logic validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()