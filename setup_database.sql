-- setup_database.sql

-- Create the database
CREATE DATABASE cfwdb;

-- Connect to the new database
\c cfwdb

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create a user for the application
CREATE USER cfwuser WITH PASSWORD '1234';

-- Grant privileges to the user
GRANT ALL PRIVILEGES ON DATABASE cfwdb TO cfwuser;

-- Grant privileges on tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cfwuser;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cfwuser;

-- Run in terminal with this command
-- psql cfwdb -f setup_database.sql