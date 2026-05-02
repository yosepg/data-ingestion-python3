-- PostgreSQL initialisation script
-- Runs automatically when the postgres container starts for the first time.

-- Ensure database exists (already created via POSTGRES_DB env var, but kept
-- here for documentation clarity)
\c customer_db;

-- Create the customers table if it doesn't already exist
CREATE TABLE IF NOT EXISTS customers (
    customer_id     VARCHAR(50)     PRIMARY KEY,
    first_name      VARCHAR(100)    NOT NULL,
    last_name       VARCHAR(100)    NOT NULL,
    email           VARCHAR(255)    NOT NULL,
    phone           VARCHAR(20),
    address         VARCHAR(255),
    date_of_birth   DATE,
    account_balance DECIMAL(15, 2),
    created_at      TIMESTAMP
);

-- Optional: index on email for fast look-ups
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers (email);
