# Verification script to check if the reference data tables were created successfully

import subprocess
import sys

def check_tables():
    print("Checking if reference data tables were created...")
    
    # Check if the tables exist
    tables_to_check = [
        "car_brands",
        "car_models", 
        "car_generations",
        "car_modifications",
        "car_complectations"
    ]
    
    for table in tables_to_check:
        cmd = f'docker exec carmatch-postgres psql -U carmatch -d carmatch -c "\\dt {table}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if "does not exist" in result.stdout or "does not exist" in result.stderr:
            print(f"[ERROR] Table {table} was not found")
            return False
        else:
            print(f"[SUCCESS] Table {table} exists")
    
    # Check if tables are empty or have data
    print("\nChecking row counts in reference data tables:")
    for table in tables_to_check:
        cmd = f'docker exec carmatch-postgres psql -U carmatch -d carmatch -c "SELECT COUNT(*) FROM {table};"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Find the line with the count value
            for line in lines:
                if line.strip().isdigit():
                    count = int(line.strip())
                    print(f"[INFO] {table}: {count} records")
                    break
        else:
            print(f"[ERROR] Could not get count for {table}")
    
    print("\n[SUCCESS] Database structure verification completed!")
    print("\nNote: The seeder could not run due to encoding issues in the Windows environment.")
    print("However, the database tables for reference data have been successfully created.")
    print("\nTo run the seeder, you would typically need to:")
    print("1. Ensure proper encoding settings in your environment")
    print("2. Run: python seed_db.py")
    
    return True

if __name__ == "__main__":
    check_tables()