#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v analyst_password="$ANALYST_PASSWORD" \
     -v dbname="$POSTGRES_DB" <<'EOSQL'
CREATE ROLE analyst LOGIN PASSWORD :'analyst_password';
GRANT CONNECT ON DATABASE :"dbname" TO analyst;
GRANT USAGE ON SCHEMA public TO analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analyst;
EOSQL