CREATE ROLE school LOGIN PASSWORD 'p';
ALTER ROLE school SET search_path = school;
CREATE DATABASE school OWNER school;