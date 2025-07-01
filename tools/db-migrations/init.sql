-- Alter8 Platform Database Initialization Script
-- This script sets up the basic database structure for the platform

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Basic setup completed
SELECT 'Database initialized successfully' as status;
