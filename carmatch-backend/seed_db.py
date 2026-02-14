#!/usr/bin/env python3
"""
Script to seed the database with car reference data from XML file.
"""

import sys
import os

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.xml_seeder import parse_xml_and_seed_database


def main():
    """
    Main function to run the seeder.
    """
    import os
    # Path relative to the carmatch-backend directory
    xml_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cars.xml")
    
    print("Starting database seeding process...")
    print(f"Using XML file: {xml_file_path}")
    
    try:
        parse_xml_and_seed_database(xml_file_path)
        print("Seeding completed successfully!")
    except FileNotFoundError:
        print(f"Error: XML file not found at {xml_file_path}")
        print("Make sure the cars.xml file exists in the project root.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during seeding: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()