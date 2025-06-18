CREATE SCHEMA main;

CREATE TABLE IF NOT EXISTS main.users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_partner_id INTEGER UNIQUE NOT NULL,
    user_code INTEGER UNIQUE NOT NULL,
    user_name TEXT NOT NULL,
    last_provider_activity TEXT,
    last_receiver_activity TEXT
);

CREATE TABLE IF NOT EXISTS main.redeem (
    redeem_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    odoo_pos_id INTEGER NOT NULL,
    redeem_datetime TEXT NOT NULL,
    redeem_user INTEGER NOT NULL REFERENCES main.users(user_id),
    redeem_value REAL NOT NULL,
    redeem_barcode TEXT NOT NULL,
    anomaly BOOL NOT NULL
);

CREATE TABLE IF NOT EXISTS main.consigne (
    consigne_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    consigne_pattern TEXT,
    consigne_name TEXT,
    consigne_barcode TEXT UNIQUE,
    consigne_barcode_base TEXT,
    consigne_active BOOL
);

CREATE TABLE IF NOT EXISTS main.product_returns (
    product_return_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    odoo_product_return_id INTEGER UNIQUE,
    product_return_name TEXT NOT NULL,
    returnable BOOL NOT NULL,
    return_value REAL
);

CREATE TABLE IF NOT EXISTS main.products (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    odoo_product_id INTEGER UNIQUE NOT NULL,
    product_name TEXT,
    barcode TEXT NOT NULL,
    product_return_id INTEGER NOT NULL REFERENCES main.product_returns(product_return_id)
);

CREATE TABLE IF NOT EXISTS main.deposits(
    deposit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    receiver_id INTEGER NOT NULL REFERENCES main.users(user_id),
    provider_id INTEGER NOT NULL REFERENCES main.users(user_id),
    deposit_datetime TEXT NOT NULL,
    closed BOOL NOT NULL,
    deposit_barcode TEXT,
    deposit_barcode_base_id INTEGER REFERENCES main.consigne(consigne_id),
    redeemed INTEGER REFERENCES main.redeem(redeem_id)
);

CREATE TABLE IF NOT EXISTS main.deposit_lines (
    deposit_line_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    deposit_id INTEGER NOT NULL REFERENCES main.deposits(deposit_id),
    product_id INTEGER NOT NULL REFERENCES main.products(product_id),
    deposit_line_datetime TEXT NOT NULL,
    canceled BOOL NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_partner_id ON main.users(user_partner_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_codes ON main.users(user_code);
CREATE UNIQUE INDEX IF NOT EXISTS idx_opid ON main.products(odoo_product_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_return_opid ON main.product_returns(odoo_product_return_id);

INSERT INTO main.product_returns (product_return_name, odoo_product_return_id, returnable, return_value)
VALUES ('Non Retournable', 0, false, NULL)
ON CONFLICT DO NOTHING;


