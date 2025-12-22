# app.py
from flask import Flask, jsonify, request
import psycopg2
import redis
import json
import os

app = Flask(__name__)

def get_secret(env_var, default=None):
    """Get secret from file if *_FILE env var is set, otherwise from env var."""
    file_path = os.getenv(f'{env_var}_FILE')
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return f.read().strip()
    return os.getenv(env_var, default)

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'db')
DB_NAME = get_secret('DB_NAME', 'ecommerce')
DB_USER = get_secret('DB_USER', 'ecomuser')
DB_PASSWORD = get_secret('DB_PASSWORD', 'securepassword123')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
# timeouts (seconds) for quick health checks
DB_CONNECT_TIMEOUT = int(os.getenv('DB_CONNECT_TIMEOUT', '3'))
REDIS_CONNECT_TIMEOUT = float(os.getenv('REDIS_CONNECT_TIMEOUT', '3'))

def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, connect_timeout=DB_CONNECT_TIMEOUT)

# Redis configuration
redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True, socket_connect_timeout=REDIS_CONNECT_TIMEOUT)

@app.route('/')
def home():
    return jsonify({
        "message": "E-commerce API",
        "status": "healthy",
        "components": ["nginx", "flask", "postgresql", "redis"]
    })

@app.route('/products')
def get_products():
    # Try cache first
    cached_products = redis_client.get('products')
    if cached_products:
        return jsonify({"source": "cache", "data": json.loads(cached_products)})
    
    # If not in cache, query database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, name, price FROM products ORDER BY id;')
        products = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert to list of dicts
        product_list = [{"id": p[0], "name": p[1], "price": float(p[2])} for p in products]
        
        # Store in cache for 2 minutes
        redis_client.setex('products', 120, json.dumps(product_list))
        
        return jsonify({"source": "database", "data": product_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/products', methods=['POST'])
def add_product():
    data = request.get_json()
    name = data.get('name')
    price = data.get('price')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO products (name, price) VALUES (%s, %s) RETURNING id;',
            (name, price)
        )
        product_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        # Invalidate cache
        redis_client.delete('products')
        
        return jsonify({"message": "Product added", "id": product_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json()
    name = data.get('name')
    price = data.get('price')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'UPDATE products SET name = %s, price = %s WHERE id = %s;',
            (name, price, product_id)
        )
        if cur.rowcount == 0:
            return jsonify({"error": "Product not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        
        # Invalidate cache
        redis_client.delete('products')
        
        return jsonify({"message": "Product updated", "id": product_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM products WHERE id = %s;', (product_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "Product not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        
        # Invalidate cache
        redis_client.delete('products')
        
        return jsonify({"message": "Product deleted", "id": product_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health_check():
    try:
        # Test database connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1;')
        cur.close()
        conn.close()
        
        # Test redis connection
        redis_client.ping()
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "nginx": "running"
        })
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)