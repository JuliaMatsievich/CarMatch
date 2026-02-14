@echo off
setlocal enabledelayedexpansion

echo Creating temporary directory...
mkdir temp_seeder 2>nul

echo Copying files...
copy "cars.xml" "temp_seeder\cars.xml" >nul
if errorlevel 1 (
    echo Error: Could not copy cars.xml
    goto cleanup
)

echo Creating seeder script...
(
echo import sys
echo import os
echo import xml.etree.ElementTree as ET
echo from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
echo from sqlalchemy.orm import sessionmaker, declarative_base
echo from sqlalchemy.dialects.postgresql import JSONB
echo.
echo def utcnow^(^):
echo     from datetime import datetime
echo     return datetime.utcnow^(^)
echo.
echo Base = declarative_base^(^)
echo.
echo class CarBrand^(Base^):
echo     __tablename__ = "car_brands"
echo     id = Column^(Integer, primary_key=True, index=True, autoincrement=True^)
echo     name = Column^(String^^(100^), nullable=False, unique=True^)
echo     code = Column^(String^^(50^), nullable=True^)
echo     created_at = Column^(DateTime, default=utcnow, nullable=False^)
echo     updated_at = Column^(DateTime, default=utcnow, onupdate=utcnow, nullable=False^)
echo.
echo class CarModel^(Base^):
echo     __tablename__ = "car_models"
echo     id = Column^(Integer, primary_key=True, index=True, autoincrement=True^)
echo     brand_id = Column^(Integer, ForeignKey^("car_brands.id", ondelete="CASCADE"^), nullable=False, index=True^)
echo     name = Column^(String^^(100^), nullable=False^)
echo     external_id = Column^(String^^(100^), nullable=True^)
echo     created_at = Column^(DateTime, default=utcnow, nullable=False^)
echo     updated_at = Column^(DateTime, default=utcnow, onupdate=utcnow, nullable=False^)
echo.
echo class CarGeneration^(Base^):
echo     __tablename__ = "car_generations"
echo     id = Column^(Integer, primary_key=True, index=True, autoincrement=True^)
echo     model_id = Column^(Integer, ForeignKey^("car_models.id", ondelete="CASCADE"^), nullable=False, index=True^)
echo     name = Column^(String^^(100^), nullable=True^)
echo     external_id = Column^(String^^(100^), nullable=True^)
echo     years = Column^(JSONB, default=dict, nullable=False^)
echo     created_at = Column^(DateTime, default=utcnow, nullable=False^)
echo     updated_at = Column^(DateTime, default=utcnow, onupdate=utcnow, nullable=False^)
echo.
echo class CarModification^(Base^):
echo     __tablename__ = "car_modifications"
echo     id = Column^(Integer, primary_key=True, index=True, autoincrement=True^)
echo     generation_id = Column^(Integer, ForeignKey^("car_generations.id", ondelete="CASCADE"^), nullable=False, index=True^)
echo     name = Column^(String^^(200^), nullable=False^)
echo     external_id = Column^(String^^(100^), nullable=True^)
echo     body_type = Column^(String^^(100^), nullable=True^)
echo     created_at = Column^(DateTime, default=utcnow, nullable=False^)
echo     updated_at = Column^(DateTime, default=utcnow, onupdate=utcnow, nullable=False^)
echo.
echo class CarComplectation^(Base^):
echo     __tablename__ = "car_complectations"
echo     id = Column^(Integer, primary_key=True, index=True, autoincrement=True^)
echo     modification_id = Column^(Integer, ForeignKey^("car_modifications.id", ondelete="CASCADE"^), nullable=False, index=True^)
echo     name = Column^(String^^(100^), nullable=False^)
echo     external_id = Column^(String^^(100^), nullable=True^)
echo     created_at = Column^(DateTime, default=utcnow, nullable=False^)
echo     updated_at = Column^(DateTime, default=utcnow, onupdate=utcnow, nullable=False^)
echo.
echo def parse_xml_and_seed_database^(xml_file_path: str^):
echo     ^"""
echo     Parse the cars.xml file and seed the database with normalized reference data.
echo     ^"""
echo     print^(f"Processing XML file: {xml_file_path}"^)
echo     
echo     # Parse the XML file
echo     tree = ET.parse^(xml_file_path^)
echo     root = tree.getroot^(^)
echo     
echo     # Create database engine and session
echo     DATABASE_URL = os.getenv^("DATABASE_URL", "postgresql+psycopg://carmatch:carmatch@postgres:5432/carmatch"^)
echo     engine = create_engine^(DATABASE_URL, pool_pre_ping=True^)
echo     Session = sessionmaker^(bind=engine^)
echo     db = Session^(^)
echo     
echo     try:
echo         # Process each car brand in the catalog
echo         processed_brands = 0
echo         processed_models = 0
echo         processed_generations = 0
echo         processed_modifications = 0
echo         processed_complectations = 0
echo         
echo         for idx, mark_elem in enumerate^(root.findall^('mark'^)^):
echo             mark_name = mark_elem.get^('name'^)
echo             code_elem = mark_elem.find^('code'^)
echo             code = code_elem.text if code_elem is not None else None
echo             
echo             print^(f"Processing brand {!idx!+1}: {mark_name}"^)
echo             
echo             # Check if brand already exists
echo             brand = db.query^(CarBrand^).filter^(CarBrand.name == mark_name^).first^(^)
echo             if not brand:
echo                 brand = CarBrand^(name=mark_name, code=code^)
echo                 db.add^(brand^)
echo                 db.flush^(^)  # Get the ID without committing
echo                 processed_brands += 1
echo             else:
echo                 print^(f"  Brand {mark_name} already exists, skipping creation"^)
echo             
echo             # Process folders (models) under this brand
echo             for folder_elem in mark_elem.findall^('folder'^):
echo                 folder_name = folder_elem.get^('name'^)
echo                 folder_id = folder_elem.get^('id'^)
echo                 
echo                 # Check if model already exists for this brand
echo                 model = db.query^(CarModel^).filter^(
echo                     CarModel.brand_id == brand.id,
echo                     CarModel.name == folder_name
echo                 ^).first^(^)
echo                 
echo                 if not model:
echo                     model = CarModel^(
echo                         brand_id=brand.id,
echo                         name=folder_name,
echo                         external_id=folder_id
echo                     ^)
echo                     db.add^(model^)
echo                     db.flush^(^)  # Get the ID without committing
echo                     processed_models += 1
echo                 else:
echo                     print^(f"    Model {folder_name} already exists for brand {mark_name}, skipping creation"^)
echo                 
echo                 # Process generations
echo                 for gen_elem in folder_elem.findall^('generation'^):
echo                     gen_id = gen_elem.get^('id'^)
echo                     gen_text = gen_elem.text
echo                     
echo                     # Check if generation already exists for this model
echo                     generation = db.query^(CarGeneration^).filter^(
echo                         CarGeneration.model_id == model.id,
echo                         CarGeneration.external_id == gen_id
echo                     ^).first^(^)
echo                     
echo                     if not generation:
echo                         generation = CarGeneration^(
echo                             model_id=model.id,
echo                             name=gen_text,
echo                             external_id=gen_id,
echo                             years={}  # Will be populated later if needed
echo                         ^)
echo                         db.add^(generation^)
echo                         db.flush^(^)  # Get the ID without committing
echo                         processed_generations += 1
echo                     else:
echo                         print^(f"      Generation {gen_text} already exists for model {folder_name}, skipping creation"^)
echo                 
echo                 # Process modifications under this folder
echo                 for mod_elem in folder_elem.findall^('modification'^):
echo                     mod_name = mod_elem.get^('name'^)
echo                     mod_id = mod_elem.get^('id'^)
echo                     
echo                     # Extract additional fields from modification
echo                     body_type_elem = mod_elem.find^('body_type'^)
echo                     body_type = body_type_elem.text if body_type_elem is not None else None
echo                     
echo                     years_elem = mod_elem.find^('years'^)
echo                     years_text = years_elem.text if years_elem is not None else None
echo                     
echo                     # Parse years range if available
echo                     years_data = {}
echo                     if years_text:
echo                         # Example: "2019 - 2021" or "2019 - н.в." (present day)
echo                         parts = years_text.split^(' - '^)
echo                         if len^(parts^) == 2:
echo                             years_data = {
echo                                 'start': parts[0],
echo                                 'end': parts[1]
echo                             }
echo                         else:
echo                             years_data = {
echo                                 'single': years_text
echo                             }
echo                     
echo                     # Check if modification already exists
echo                     modification = db.query^(CarModification^).filter^(
echo                         CarModification.generation_id == generation.id,
echo                         CarModification.external_id == mod_id
echo                     ^).first^(^)
echo                     
echo                     if not modification:
echo                         modification = CarModification^(
echo                             generation_id=generation.id,
echo                             name=mod_name,
echo                             external_id=mod_id,
echo                             body_type=body_type
echo                         ^)
echo                         db.add^(modification^)
echo                         db.flush^(^)  # Get the ID without committing
echo                         processed_modifications += 1
echo                     else:
echo                         print^(f"      Modification {mod_name} already exists for generation {gen_text}, skipping creation"^)
echo                     
echo                     # Process complectations under this modification
echo                     complectations_elem = mod_elem.find^('complectations'^)
echo                     if complectations_elem is not None:
echo                         for comp_elem in complectations_elem.findall^('complectation'^):
echo                             comp_name = comp_elem.text
echo                             comp_id = comp_elem.get^('id'^)
echo                             
echo                             # Check if complectation already exists
echo                             complectation = db.query^(CarComplectation^).filter^(
echo                                 CarComplectation.modification_id == modification.id,
echo                                 CarComplectation.external_id == comp_id
echo                             ^).first^(^)
echo                             
echo                             if not complectation:
echo                                 complectation = CarComplectation^(
echo                                     modification_id=modification.id,
echo                                     name=comp_name,
echo                                     external_id=comp_id
echo                                 ^)
echo                                 db.add^(complectation^)
echo                                 processed_complectations += 1
echo                             else:
echo                                 print^(f"        Complectation {comp_name} already exists for modification {mod_name}, skipping creation"^)
echo         
echo         # Commit all changes to the database
echo         db.commit^(^)
echo         print^(f"Database seeding completed successfully!"^)
echo         print^(f"Processed: {processed_brands} brands, {processed_models} models, {processed_generations} generations, {processed_modifications} modifications, {processed_complectations} complectations"^)
echo         
echo     except Exception as e:
echo         # Rollback in case of error
echo         db.rollback^(^)
echo         print^(f"Error during seeding: {str^(e^)}"^)
echo         raise e
echo     finally:
echo         db.close^(^)
echo.
echo if __name__ == "__main__":
echo     xml_file_path = "/app/cars.xml"  # Path inside container
echo     print^("Starting database seeding process..."^)
echo     print^(f"Using XML file: {xml_file_path}"^)
echo     
echo     try:
echo         parse_xml_and_seed_database^(xml_file_path^)
echo         print^("Seeding completed successfully!"^)
echo     except Exception as e:
echo         print^(f"Error during seeding: {str^(e^)}"^)
echo         import traceback
echo         traceback.print_exc^(^)
echo         sys.exit^(1^)
) > "temp_seeder\seeder.py"

echo Creating requirements file...
(
echo sqlalchemy>=2.0
echo psycopg[binary]>=3.1
) > "temp_seeder\requirements.txt"

echo Running seeder in Python container...
docker run --rm ^
    --network=container:carmatch-postgres ^
    -v "%cd%\temp_seeder:/app" ^
    python:3.10-slim ^
    sh -c "cd /app && pip install --no-cache-dir -r requirements.txt && python seeder.py"

:cleanup
echo Removing temporary directory...
rmdir /s /q temp_seeder 2>nul
echo Done.