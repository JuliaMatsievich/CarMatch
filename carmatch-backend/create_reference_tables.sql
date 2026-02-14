-- SQL script to create car reference data tables

-- Create car_brands table
CREATE TABLE IF NOT EXISTS car_brands (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_car_brands_id ON car_brands(id);
CREATE INDEX IF NOT EXISTS idx_car_brands_name ON car_brands(name);

-- Create car_models table
CREATE TABLE IF NOT EXISTS car_models (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER NOT NULL REFERENCES car_brands(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    external_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_car_models_id ON car_models(id);
CREATE INDEX IF NOT EXISTS idx_car_models_brand ON car_models(brand_id);
CREATE INDEX IF NOT EXISTS idx_car_models_name ON car_models(name);
CREATE INDEX IF NOT EXISTS idx_car_models_external_id ON car_models(external_id);

-- Create car_generations table
CREATE TABLE IF NOT EXISTS car_generations (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES car_models(id) ON DELETE CASCADE,
    name VARCHAR(100),
    external_id VARCHAR(100),
    years JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_car_generations_id ON car_generations(id);
CREATE INDEX IF NOT EXISTS idx_car_generations_model ON car_generations(model_id);
CREATE INDEX IF NOT EXISTS idx_car_generations_external_id ON car_generations(external_id);

-- Create car_modifications table
CREATE TABLE IF NOT EXISTS car_modifications (
    id SERIAL PRIMARY KEY,
    generation_id INTEGER NOT NULL REFERENCES car_generations(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    external_id VARCHAR(100),
    body_type VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_car_modifications_id ON car_modifications(id);
CREATE INDEX IF NOT EXISTS idx_car_modifications_generation ON car_modifications(generation_id);
CREATE INDEX IF NOT EXISTS idx_car_modifications_external_id ON car_modifications(external_id);

-- Create car_complectations table
CREATE TABLE IF NOT EXISTS car_complectations (
    id SERIAL PRIMARY KEY,
    modification_id INTEGER NOT NULL REFERENCES car_modifications(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    external_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_car_complectations_id ON car_complectations(id);
CREATE INDEX IF NOT EXISTS idx_car_complectations_modification ON car_complectations(modification_id);
CREATE INDEX IF NOT EXISTS idx_car_complectations_external_id ON car_complectations(external_id);

-- Add foreign key columns to cars table
ALTER TABLE cars ADD COLUMN IF NOT EXISTS brand_id INTEGER REFERENCES car_brands(id) ON DELETE SET NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS model_id INTEGER REFERENCES car_models(id) ON DELETE SET NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS generation_id INTEGER REFERENCES car_generations(id) ON DELETE SET NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS modification_id INTEGER REFERENCES car_modifications(id) ON DELETE SET NULL;

-- Create indexes for the new foreign key columns
CREATE INDEX IF NOT EXISTS idx_cars_brand ON cars(brand_id);
CREATE INDEX IF NOT EXISTS idx_cars_model ON cars(model_id);
CREATE INDEX IF NOT EXISTS idx_cars_generation ON cars(generation_id);
CREATE INDEX IF NOT EXISTS idx_cars_modification ON cars(modification_id);

-- Update alembic version
INSERT INTO alembic_version (version_num) VALUES ('4') ON CONFLICT DO NOTHING;