#!/bin/bash

echo "> Creating database '""${DB_NAME}""' and '""${DB_USERNAME}""' user"
psql \
  --username postgres \
  --command "CREATE DATABASE ""${DB_NAME}"";"

psql \
  --username postgres \
  --command "CREATE USER ${DB_USERNAME} WITH ENCRYPTED PASSWORD '${DB_PASSWORD}';"

echo "Done."

echo "> Executing /home/psql_schema.sql script."
psql \
  --username postgres \
  --file /home/psql_schema.sql \
  "${DB_NAME}"

echo "Done."

echo "> GRANTING PRIVILEGES to '""${DB_USERNAME}""' user for '""${DB_NAME}""' database"
psql \
  --username postgres \
  --command "GRANT CONNECT ON DATABASE ${DB_NAME} TO ${DB_USERNAME};"

psql \
  --username postgres \
  --command "GRANT ALL ON SCHEMA main TO ${DB_USERNAME};" \
  "${DB_NAME}"

psql \
  --username postgres \
  --command "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA main TO ${DB_USERNAME};" \
  "${DB_NAME}"

echo "Done."