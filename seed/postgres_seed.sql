-- ============================================
-- Realistic e-commerce schema with performance problems
-- Intentionally missing indexes and bad patterns for the MCP server to find
-- ============================================

-- Orders table: high volume, missing index on status + created_at
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price NUMERIC(10, 2) NOT NULL,
    stock INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- INTENTIONAL: No index on customer_id, status, or created_at
-- This will show up as slow queries when filtering/joining
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    total NUMERIC(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- INTENTIONAL: No index on order_id
CREATE TABLE IF NOT EXISTS order_logs (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    action VARCHAR(100),
    details TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed 10K customers
INSERT INTO customers (email, name, country)
SELECT
    'user' || i || '@example.com',
    'Customer ' || i,
    (ARRAY['US', 'MX', 'BR', 'AR', 'CO', 'CL', 'PE'])[1 + (i % 7)]
FROM generate_series(1, 10000) AS i;

-- Seed 500 products
INSERT INTO products (name, category, price, stock)
SELECT
    'Product ' || i,
    (ARRAY['electronics', 'clothing', 'food', 'books', 'toys'])[1 + (i % 5)],
    (RANDOM() * 500 + 1)::NUMERIC(10, 2),
    (RANDOM() * 1000)::INTEGER
FROM generate_series(1, 500) AS i;

-- Seed 50K orders (enough to make missing indexes noticeable)
INSERT INTO orders (customer_id, product_id, quantity, total, status, created_at)
SELECT
    1 + (RANDOM() * 9999)::INTEGER,
    1 + (RANDOM() * 499)::INTEGER,
    1 + (RANDOM() * 5)::INTEGER,
    (RANDOM() * 1000 + 10)::NUMERIC(10, 2),
    (ARRAY['pending', 'processing', 'shipped', 'delivered', 'cancelled'])[1 + (i % 5)],
    NOW() - (RANDOM() * INTERVAL '365 days')
FROM generate_series(1, 50000) AS i;

-- Seed 100K order logs
INSERT INTO order_logs (order_id, action, details, created_at)
SELECT
    1 + (RANDOM() * 49999)::INTEGER,
    (ARRAY['created', 'updated', 'status_change', 'payment', 'refund'])[1 + (i % 5)],
    'Log entry for action ' || i,
    NOW() - (RANDOM() * INTERVAL '365 days')
FROM generate_series(1, 100000) AS i;

-- Run some queries to populate pg_stat_statements
-- These are intentionally slow (full table scans)
SELECT COUNT(*) FROM orders WHERE status = 'pending' AND created_at > NOW() - INTERVAL '30 days';
SELECT c.name, SUM(o.total) FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.name ORDER BY SUM(o.total) DESC LIMIT 10;
SELECT * FROM order_logs WHERE order_id IN (SELECT id FROM orders WHERE status = 'cancelled');
SELECT o.*, c.email FROM orders o JOIN customers c ON c.id = o.customer_id WHERE c.country = 'MX' AND o.status = 'shipped';
SELECT product_id, AVG(total), COUNT(*) FROM orders GROUP BY product_id HAVING COUNT(*) > 50;

-- Force stats collection
SELECT pg_stat_statements_reset();

-- Re-run to capture in stats
SELECT COUNT(*) FROM orders WHERE status = 'pending' AND created_at > NOW() - INTERVAL '30 days';
SELECT c.name, SUM(o.total) FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.name ORDER BY SUM(o.total) DESC LIMIT 10;
SELECT * FROM order_logs WHERE order_id IN (SELECT id FROM orders WHERE status = 'cancelled');
