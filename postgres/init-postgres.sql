-- Initialize PostgreSQL databases for both Orthanc instances

-- Create database for Orthanc 1
CREATE DATABASE orthanc1;

-- Create database for Orthanc 2  
CREATE DATABASE orthanc2;

-- Grant permissions to orthanc user for both databases
GRANT ALL PRIVILEGES ON DATABASE orthanc1 TO orthanc;
GRANT ALL PRIVILEGES ON DATABASE orthanc2 TO orthanc;
