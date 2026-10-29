CREATE ROLE analyst LOGIN PASSWORD 'analyst_demo';
GRANT CONNECT ON DATABASE sales TO analyst;
GRANT USAGE ON SCHEMA public TO analyst;
GRANT SELECT ON products, sales TO analyst;