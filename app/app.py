# app.py
from flask import Flask, jsonify, request
import psycopg2
import redis
import json
import os

app = Flask(__name__)

# Database configuration
DB_HOST = os.getenv('DB_HOST', '192.168.123.46')
DB_NAME = os.getenv('DB_NAME', 'ecommerce')
DB_USER = os.getenv('DB_USER', 'ecomuser')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'securepassword123')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
# timeouts (seconds) for quick health checks
DB_CONNECT_TIMEOUT = int(os.getenv('DB_CONNECT_TIMEOUT', '3'))
REDIS_CONNECT_TIMEOUT = float(os.getenv('REDIS_CONNECT_TIMEOUT', '3'))

def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, connect_timeout=DB_CONNECT_TIMEOUT)

# Redis configuration
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=REDIS_CONNECT_TIMEOUT)

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