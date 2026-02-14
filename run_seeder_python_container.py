# Alternative approach: Run seeder using a Python container connected to the PostgreSQL network

import subprocess
import sys
import os
import tempfile

def run_seeder_with_python_container():
    print("Running seeder using a Python container...")
    
    # Create a temporary directory for our work
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create the seeder script in the temp directory
        seeder_script = '''#!/usr/bin/env python3
import sys
import os
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB

def utcnow():
    from datetime import datetime
    return datetime.utcnow()

Base = declarative_base()

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
    brand_id = Column(Integer, ForeignKey("car_brands.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    external_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

class CarGeneration(Base):
    __tablename__ = "car_generations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("car_models.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=True)
    external_id = Column(String(100), nullable=True)
    years = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

class CarModification(Base):
    __tablename__ = "car_modifications"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    generation_id = Column(Integer, ForeignKey("car_generations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    external_id = Column(String(100), nullable=True)
    body_type = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

class CarComplectation(Base):
    __tablename__ = "car_complectations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    modification_id = Column(Integer, ForeignKey("car_modifications.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    external_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

def parse_xml_and_seed_database(xml_file_path: str):
    """
    Parse the cars.xml file and seed the database with normalized reference data.
    """
    print(f"Parsing XML file: {xml_file_path}")
    
    # Parse the XML file
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    # Create database engine and session
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://carmatch:carmatch@postgres:5432/carmatch")
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Process each car brand (mark) in the catalog
        processed_brands = 0
        processed_models = 0
        processed_generations = 0
        processed_modifications = 0
        processed_complectations = 0
        
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
                processed_brands += 1
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
                    processed_models += 1
                else:
                    print(f"    Model {folder_name} already exists for brand {mark_name}, skipping creation")
                
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
                        processed_generations += 1
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
                        processed_modifications += 1
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
                                processed_complectations += 1
                            else:
                                print(f"        Complectation {comp_name} already exists for modification {mod_name}, skipping creation")
        
        # Commit all changes to the database
        db.commit()
        print(f"Database seeding completed successfully!")
        print(f"Processed: {processed_brands} brands, {processed_models} models, {processed_generations} generations, {processed_modifications} modifications, {processed_complectations} complectations")
        
    except Exception as e:
        # Rollback in case of error
        db.rollback()
        print(f"Error during seeding: {str(e)}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    xml_file_path = "/app/cars.xml"
    print("Starting database seeding process...")
    print(f"Using XML file: {xml_file_path}")
    
    try:
        parse_xml_and_seed_database(xml_file_path)
        print("Seeding completed successfully!")
    except Exception as e:
        print(f"Error during seeding: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
'''
        
        # Write the seeder script to a file in the temp directory
        seeder_path = os.path.join(temp_dir, "seeder.py")
        with open(seeder_path, "w", encoding="utf-8") as f:
            f.write(seeder_script)
        
        # Copy the cars.xml to the temp directory
        xml_path = os.path.join(temp_dir, "cars.xml")
        import shutil
        shutil.copy("cars.xml", xml_path)
        
        # Create a requirements file
        requirements_content = '''sqlalchemy>=2.0
psycopg[binary]>=3.1
'''
        requirements_path = os.path.join(temp_dir, "requirements.txt")
        with open(requirements_path, "w") as f:
            f.write(requirements_content)
        
        # Run the seeder in a Python container connected to the same network as postgres
        print("Running seeder in Python container...")
        
        # Build and run the container
        cmd = [
            "docker", "run", "--rm",
            "--network", "container:carmatch-postgres",  # Connect to the same network as postgres
            "-v", f"{temp_dir}:/app",
            "python:3.10-slim",
            "sh", "-c", 
            "cd /app && pip install --no-cache-dir -r requirements.txt && python seeder.py"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("Seeder completed successfully!")
            return True
        else:
            print(f"Seeder failed with return code {result.returncode}")
            return False

if __name__ == "__main__":
    success = run_seeder_with_python_container()
    if success:
        print("\n[SUCCESS] Database seeding completed!")
    else:
        print("\n[ERROR] Database seeding failed!")
        sys.exit(1)