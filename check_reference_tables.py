import os
from sqlalchemy import create_engine, text

# Use the local database URL (since we're connecting from outside Docker)
DATABASE_URL = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

try:
    with engine.connect() as connection:
        print("Connected to PostgreSQL database!")
        
        # Check the reference tables
        print(f"\nChecking reference tables:")
        
        # Check car_brands table
        result = connection.execute(text("SELECT COUNT(*) FROM car_brands;"))
        total_brands = result.fetchone()[0]
        print(f"Total car brands: {total_brands}")
        
        # Check car_models table
        result = connection.execute(text("SELECT COUNT(*) FROM car_models;"))
        total_models = result.fetchone()[0]
        print(f"Total car models: {total_models}")
        
        # Check car_generations table
        result = connection.execute(text("SELECT COUNT(*) FROM car_generations;"))
        total_gens = result.fetchone()[0]
        print(f"Total car generations: {total_gens}")
        
        # Check car_modifications table
        result = connection.execute(text("SELECT COUNT(*) FROM car_modifications;"))
        total_mods = result.fetchone()[0]
        print(f"Total car modifications: {total_mods}")
        
        # Check car_complectations table
        result = connection.execute(text("SELECT COUNT(*) FROM car_complectations;"))
        total_comps = result.fetchone()[0]
        print(f"Total car complectations: {total_comps}")
        
        # Check if any of the reference tables have year information
        if total_gens > 0:
            result = connection.execute(text("SELECT COUNT(*) FROM car_generations WHERE years != '{}';"))
            gens_with_years = result.fetchone()[0]
            print(f"Generations with year data: {gens_with_years}")
            
            if gens_with_years > 0:
                result = connection.execute(text("""
                    SELECT id, name, years 
                    FROM car_generations 
                    WHERE years != '{}' 
                    LIMIT 5;
                """))
                sample_gens = result.fetchall()
                print(f"\nSample generations with year data:")
                for gen in sample_gens:
                    print(f"  ID: {gen[0]}, Name: {gen[1]}, Years: {gen[2]}")
        
        print(f"\nChecking the main cars table:")
        # Check sample data to see if year values are populated
        result = connection.execute(text("SELECT COUNT(*) FROM cars;"))
        total_cars = result.fetchone()[0]
        print(f"Total cars in table: {total_cars}")
        
        if total_cars > 0:
            result = connection.execute(text("SELECT COUNT(*) FROM cars WHERE year IS NOT NULL;"))
            cars_with_year = result.fetchone()[0]
            print(f"Cars with year data: {cars_with_year}")
            
            if cars_with_year > 0:
                # Show some sample records with year data
                result = connection.execute(text("""
                    SELECT id, mark_name, model_name, year, body_type 
                    FROM cars 
                    WHERE year IS NOT NULL 
                    LIMIT 10;
                """))
                sample_records = result.fetchall()
                print(f"\nSample records with year data:")
                for record in sample_records:
                    print(f"  ID: {record[0]}, Brand: {record[1]}, Model: {record[2]}, Year: {record[3]}, Body: {record[4]}")
            else:
                print("\nNo cars have year data populated!")
        else:
            print("\nThe cars table is empty - no data has been loaded from the XML file yet.")

except Exception as e:
    print(f"Database connection failed: {str(e)}")
    import traceback
    traceback.print_exc()