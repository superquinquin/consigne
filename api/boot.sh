#!/bin/sh
# cat database/schema.sql | sqlite3 database.db
sanic asgi:app --no-motd --workers 2