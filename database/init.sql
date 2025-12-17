-- init.sql

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

GRANT ALL PRIVILEGES ON TABLE products TO CURRENT_USER;

-- Insert sample data
INSERT INTO products (name, price) VALUES 
    ('Laptop', 999.99),
    ('Smartphone', 699.99),
    ('Headphones', 149.99),
    ('Tablet', 399.99),
    ('Smart Watch', 199.99)
ON CONFLICT DO NOTHING;