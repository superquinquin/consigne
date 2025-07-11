CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    user_partner_id INTEGER UNIQUE NOT NULL,
    user_code INTEGER UNIQUE NOT NULL,
    user_name TEXT NOT NULL,
    last_provider_activity TEXT,
    last_receiver_activity TEXT
);

CREATE TABLE IF NOT EXISTS  deposits(
    deposit_id INTEGER PRIMARY KEY,
    receiver_id INTEGER NOT NULL REFERENCES users(user_id),
    provider_id INTEGER NOT NULL REFERENCES users(user_id),
    deposit_datetime TEXT NOT NULL,
    closed BOOL NOT NULL,
    deposit_barcode TEXT,
    deposit_barcode_base_id INTEGER REFERENCES consigne(consigne_id),
    redeemed INTEGER REFERENCES redeem(redeem_id)
);

CREATE TABLE IF NOT EXISTS deposit_lines (
    deposit_line_id INTEGER PRIMARY KEY,
    deposit_id INTEGER NOT NULL REFERENCES deposits(deposit_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    deposit_line_datetime TEXT NOT NULL,
    canceled BOOL NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    odoo_product_id INTEGER UNIQUE NOT NULL,
    product_name TEXT,
    barcode TEXT NOT NULL,
    product_return_id INTEGER NOT NULL REFERENCES product_returns(product_return_id)
);

CREATE TABLE IF NOT EXISTS product_returns (
    product_return_id INTEGER PRIMARY KEY,
    odoo_product_return_id INTEGER UNIQUE,
    product_return_name TEXT NOT NULL,
    returnable BOOL NOT NULL,
    return_value REAL
);

CREATE TABLE IF NOT EXISTS redeem (
    redeem_id INTEGER PRIMARY KEY,
    odoo_pos_id INTEGER NOT NULL,
    redeem_datetime TEXT NOT NULL,
    redeem_user INTEGER NOT NULL REFERENCES users(user_id),
    redeem_value REAL NOT NULL,
    redeem_barcode TEXT NOT NULL,
    anomaly BOOL NOT NULL
);

CREATE TABLE IF NOT EXISTS consigne (
    consigne_id INTEGER PRIMARY KEY,
    consigne_pattern TEXT,
    consigne_name TEXT,
    consigne_barcode TEXT UNIQUE,
    consigne_barcode_base TEXT,
    consigne_active BOOL
);


CREATE UNIQUE INDEX IF NOT EXISTS idx_users_partner_id ON users(user_partner_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_codes ON users(user_code);
CREATE UNIQUE INDEX IF NOT EXISTS idx_opid ON products(odoo_product_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_return_opid ON product_returns(odoo_product_return_id);

INSERT OR IGNORE INTO product_returns (product_return_name, odoo_product_return_id, returnable, return_value)
VALUES ("Non Retournable", 0, false, NULL), ("Réutilisable", 1, true, 0.0);