import os
from sqlalchemy import create_engine, text

# Use the local database URL (since we're connecting from outside Docker)
DATABASE_URL = "postgresql+psycopg://carmatch:carmatch@localhost:5433/carmatch"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

try:
    with engine.connect() as connection:
        print("Connected to PostgreSQL database!")
        
        # Check if the cars table exists
        result = connection.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'cars'
            );
        """))
        cars_table_exists = result.fetchone()[0]
        
        if not cars_table_exists:
            print("ERROR: 'cars' table does not exist in the database!")
        else:
            print("Found 'cars' table in the database.")
            
            # Check the structure of the cars table
            result = connection.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'cars' 
                ORDER BY ordinal_position;
            """))
            columns = result.fetchall()
            print(f"\nColumns in 'cars' table:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]}")
            
            # Check if the 'year' column exists
            year_column_exists = any(col[0] == 'year' for col in columns)
            if not year_column_exists:
                print("\nERROR: 'year' column does not exist in the 'cars' table!")
            else:
                print("\nFound 'year' column in the 'cars' table.")
                
                # Check sample data to see if year values are populated
                result = connection.execute(text("SELECT COUNT(*) FROM cars;"))
                total_cars = result.fetchone()[0]
                print(f"\nTotal cars in table: {total_cars}")
                
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
                        
                    # Also check the reference tables that should contain year information
                    print(f"\nChecking reference tables that might contain year information:")
                    
                    # Check car_generations table which should have years
                    result = connection.execute(text("SELECT COUNT(*) FROM car_generations;"))
                    total_gens = result.fetchone()[0]
                    print(f"Total car generations: {total_gens}")
                    
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

except Exception as e:
    print(f"Database connection failed: {str(e)}")
    import traceback
    traceback.print_exc()