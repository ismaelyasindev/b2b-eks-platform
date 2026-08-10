#!/bin/bash
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
    CREATE SCHEMA IF NOT EXISTS auth_schema;
    CREATE SCHEMA IF NOT EXISTS product_schema;
    CREATE SCHEMA IF NOT EXISTS order_schema;
    CREATE SCHEMA IF NOT EXISTS payment_schema;
    CREATE SCHEMA IF NOT EXISTS notification_schema;

    CREATE ROLE auth_user         LOGIN PASSWORD '${AUTH_PW}';
    CREATE ROLE product_user      LOGIN PASSWORD '${PRODUCT_PW}';
    CREATE ROLE order_user        LOGIN PASSWORD '${ORDER_PW}';
    CREATE ROLE payment_user      LOGIN PASSWORD '${PAYMENT_PW}';
    CREATE ROLE notification_user LOGIN PASSWORD '${NOTIFICATION_PW}';

    GRANT USAGE, CREATE ON SCHEMA auth_schema         TO auth_user;
    GRANT USAGE, CREATE ON SCHEMA product_schema      TO product_user;
    GRANT USAGE, CREATE ON SCHEMA order_schema        TO order_user;
    GRANT USAGE, CREATE ON SCHEMA payment_schema      TO payment_user;
    GRANT USAGE, CREATE ON SCHEMA notification_schema TO notification_user;

    CREATE ROLE exporter_user LOGIN PASSWORD '${EXPORTER_PW}';
    GRANT pg_monitor TO exporter_user;

    REVOKE ALL ON SCHEMA public FROM PUBLIC;
SQL
