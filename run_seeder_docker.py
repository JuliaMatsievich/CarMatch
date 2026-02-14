# Script to run the seeder in a Python container connected to the PostgreSQL network

import subprocess
import sys
import os

def run_seeder_in_docker():
    print("Running seeder in Docker container...")
    
    # Create a simple Python script to run the seeder
    seeder_script = '''
import sys
import os
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the Python path to import our modules
sys.path.insert(0, '/app')

# Import the models
from models import Base, CarBrand, CarModel, CarGeneration, CarModification, CarComplectation

def utcnow():
    from datetime import datetime
    return datetime.utcnow()

# Define models here to avoid import issues
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

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

if __name__ == "__main__":
    xml_file_path = "/tmp/cars.xml"
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

    # Write the seeder script to a temporary file
    with open("temp_seeder.py", "w", encoding="utf-8") as f:
        f.write(seeder_script)
    
    try:
        # Copy the XML file to the postgres container
        print("Copying XML file to postgres container...")
        result = subprocess.run([
            "docker", "cp", "cars.xml", "carmatch-postgres:/tmp/cars.xml"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error copying XML file: {result.stderr}")
            return False
        
        # Copy the seeder script to the postgres container
        print("Copying seeder script to postgres container...")
        result = subprocess.run([
            "docker", "cp", "temp_seeder.py", "carmatch-postgres:/tmp/seeder.py"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error copying seeder script: {result.stderr}")
            return False
        
        # Install python packages in the postgres container temporarily
        print("Installing required Python packages in postgres container...")
        result = subprocess.run([
            "docker", "exec", "carmatch-postgres", "sh", "-c", 
            "apt-get update && apt-get install -y python3 python3-pip && pip3 install sqlalchemy psycopg"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error installing packages: {result.stderr}")
            # This might fail if the packages are already installed, which is OK
            print("Continuing anyway...")
        
        # Run the seeder script in the postgres container
        print("Running the seeder script in the postgres container...")
        result = subprocess.run([
            "docker", "exec", "carmatch-postgres", "python3", "/tmp/seeder.py"
        ], capture_output=True, text=True)
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("Seeder completed successfully!")
            return True
        else:
            print(f"Seeder failed with return code {result.returncode}")
            return False
            
    finally:
        # Clean up temporary files
        if os.path.exists("temp_seeder.py"):
            os.remove("temp_seeder.py")

if __name__ == "__main__":
    success = run_seeder_in_docker()
    if success:
        print("\\n[SUCCESS] Database seeding completed!")
    else:
        print("\\n[ERROR] Database seeding failed!")
        sys.exit(1)