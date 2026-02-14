# CarMatch Reference Data Seeder

This document describes how to set up and run the reference data seeder for the CarMatch application.

## Overview

The seeder populates the database with normalized car reference data from the `cars.xml` file. The data is organized in a hierarchical structure:

- **Car Brands** - Car manufacturers (e.g., Toyota, BMW)
- **Car Models** - Specific model lines (e.g., Camry, X5)
- **Car Generations** - Different generations of models (e.g., 2015-2020 Camry)
- **Car Modifications** - Specific trims/engines (e.g., 2.5L Automatic)
- **Car Complectations** - Equipment packages (e.g., Premium Package)

## Database Schema

The following tables are created for storing reference data:

- `car_brands` - Stores car manufacturers
- `car_models` - Stores car models linked to brands
- `car_generations` - Stores model generations linked to models
- `car_modifications` - Stores specific modifications linked to generations
- `car_complectations` - Stores equipment packages linked to modifications

The existing `cars` table has been extended with foreign keys to link to this normalized reference data.

## Setup Instructions

### Prerequisites

1. PostgreSQL server running on `localhost:5432`
2. Database named `carmatch` created
3. Environment variables configured (see `.env.example`)

### Steps

1. **Set up the database:**
   ```bash
   # Navigate to the backend directory
   cd carmatch-backend
   
   # Run database migrations to create all tables including reference data tables
   python -m alembic upgrade head
   ```

2. **Run the seeder:**
   ```bash
   # From the carmatch-backend directory
   python seed_db.py
   ```

### Alternative: Using Docker

If you prefer to use Docker to set up the database:

```bash
# From the carmatch-backend directory
docker-compose up -d postgres

# Wait for PostgreSQL to be ready, then run migrations
python -m alembic upgrade head

# Run the seeder
python seed_db.py
```

## Verification

After running the seeder, you can verify the data was loaded correctly:

```sql
SELECT COUNT(*) FROM car_brands;
SELECT COUNT(*) FROM car_models;
SELECT COUNT(*) FROM car_generations;
SELECT COUNT(*) FROM car_modifications;
SELECT COUNT(*) FROM car_complectations;
```

## Troubleshooting

- **Database Connection Error**: Ensure PostgreSQL is running and the connection details in your `.env` file are correct.
- **Database Does Not Exist**: Create the `carmatch` database in PostgreSQL before running migrations.
- **Migration Errors**: Check that your database user has sufficient privileges to create tables and indexes.
- **Large XML File**: The seeder may take some time to process the large `cars.xml` file depending on your system resources.