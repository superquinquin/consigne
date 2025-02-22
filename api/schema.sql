
"""WORK IN PROGRESS"""

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    code TEXT,
    name TEXT,
    last_provider_activity DATETIME,
    last_receiver_activity DATETIME
);

CREATE TABLE IF NOT EXISTS  deposits(
    id INTEGER PRIMARY KEY,
    receiver_id INTEGER REFERENCES users(id),
    provider_id INTEGER REFERENCES users(id),
    datetime DATETIME
);

CREATE TABLE IF NOT EXISTS deposits_line (
    id INTEGER PRIMARY KEY,
    deposit_id INTEGER REFERENCES deposits(id),
    product_id INTEGER REFERENCES products(id),
    datetime DATETIME,
    canceled BOOL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    odoo_product_id INTEGER,
    barcode TEXT,
    returnable BOOL,
    deposit_value REAL
);