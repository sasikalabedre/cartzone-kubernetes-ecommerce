import os
import time
from flask import Flask, jsonify, request
import psycopg

app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST", "cartzone-postgres")
DB_NAME = os.getenv("POSTGRES_DB", "cartzone")
DB_USER = os.getenv("POSTGRES_USER", "cartzone_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")


def get_connection():
    return psycopg.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        connect_timeout=3
    )


def initialize_database():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    price NUMERIC(10, 2) NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(id),
                    quantity INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                INSERT INTO products (name, price)
                SELECT 'Keyboard', 1200.00
                WHERE NOT EXISTS (
                    SELECT 1 FROM products WHERE name = 'Keyboard'
                )
            """)
            cur.execute("""
                INSERT INTO products (name, price)
                SELECT 'Mouse', 600.00
                WHERE NOT EXISTS (
                    SELECT 1 FROM products WHERE name = 'Mouse'
                )
            """)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "version": "v2"
    }), 200

@app.route("/products", methods=["GET"])
def products():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, price FROM products ORDER BY id")
                rows = cur.fetchall()

        return jsonify([
            {"id": row[0], "name": row[1], "price": float(row[2])}
            for row in rows
        ])
    except Exception:
        app.logger.exception("Could not fetch products")
        return jsonify({"error": "Database unavailable"}), 503


@app.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity")

    if (
        not isinstance(product_id, int)
        or isinstance(product_id, bool)
        or not isinstance(quantity, int)
        or isinstance(quantity, bool)
        or product_id < 1
        or quantity < 1
    ):
        return jsonify({
            "error": "Provide a positive integer product_id and quantity"
        }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO orders (product_id, quantity)
                    VALUES (%s, %s)
                    RETURNING id, product_id, quantity, created_at
                    """,
                    (product_id, quantity)
                )
                order = cur.fetchone()

        return jsonify({
            "id": order[0],
            "product_id": order[1],
            "quantity": order[2],
            "created_at": order[3].isoformat()
        }), 201
    except psycopg.errors.ForeignKeyViolation:
        return jsonify({"error": "Product not found"}), 404
    except Exception:
        app.logger.exception("Could not create order")
        return jsonify({"error": "Database unavailable"}), 503


if __name__ == "__main__":
    for attempt in range(10):
        try:
            initialize_database()
            break
        except Exception:
            app.logger.warning("Database not ready; retry %s/10", attempt + 1)
            if attempt == 9:
                raise
            time.sleep(3)

    app.run(host="0.0.0.0", port=5000)
