import os
import csv
import json
from datetime import datetime
from functools import wraps
import jwt
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

SECRET_KEY = os.environ.get("JWT_SECRET", "shaan_parfumerie_secret_signature_2026")
ADMIN_USER = "admin"
ADMIN_PASS = "123456"  # Change via Render Environment Variables later!

ORDERS_FILE = "orders.csv"
PRODUCTS_FILE = "products.json"

if not os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["order_id", "timestamp", "customer", "items", "total", "status"])

if not os.path.exists(PRODUCTS_FILE):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

def read_stored_orders():
    orders = []
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                orders.append({
                    "id": row["order_id"], "timestamp": row["timestamp"], "customer": row["customer"],
                    "items": row["items"], "total": float(row["total"] or 0), "status": row["status"]
                })
    return orders

def write_stored_orders(orders_list):
    with open(ORDERS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "timestamp", "customer", "items", "total", "status"])
        for o in orders_list:
            writer.writerow([o["id"], o["timestamp"], o["customer"], o["items"], o["total"], o["status"]])

def token_required(f):
    @wraps(f)
    def verification_handler(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "): return jsonify({"error": "Missing token"}), 401
        try:
            jwt.decode(auth.split(" ")[1], SECRET_KEY, algorithms=["HS256"])
        except: return jsonify({"error": "Invalid token"}), 403
        return f(*args, **kwargs)
    return verification_handler

@app.route("/", methods=["GET"])
def system_heartbeat(): return jsonify({"status": "operational"}), 200

@app.route("/login", methods=["POST"])
def perform_admin_auth():
    data = request.json or {}
    if data.get("username") == ADMIN_USER and data.get("password") == ADMIN_PASS:
        token = jwt.encode({"user": ADMIN_USER, "exp": int(datetime.utcnow().timestamp()) + 21600}, SECRET_KEY, algorithm="HS256")
        return jsonify({"token": token}), 200
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/stats", methods=["GET"])
def aggregate_dashboard_metrics():
    orders = read_stored_orders()
    revenue = sum(o["total"] for o in orders if o["status"] == "Completed")
    pending = sum(1 for o in orders if o["status"] == "Pending")
    try: prods = len(json.load(open(PRODUCTS_FILE, "r")))
    except: prods = 0
    return jsonify({"totalRevenue": revenue, "pendingOrders": pending, "totalProductsListed": prods}), 200

@app.route("/products", methods=["GET"])
def fetch_active_inventory():
    try: return jsonify(json.load(open(PRODUCTS_FILE, "r"))), 200
    except: return jsonify([]), 200

@app.route("/products", methods=["POST"])
@token_required
def inject_inventory_item():
    data = request.json or {}
    try: current_catalog = json.load(open(PRODUCTS_FILE, "r"))
    except: current_catalog = []
    
    new_product_node = {
        "id": len(current_catalog) + 1, "name": str(data.get("name")), "quantity": str(data.get("quantity", "100 ml")),
        "price": float(data.get("price")), "category": str(data.get("category")), "img": str(data.get("img"))
    }
    current_catalog.append(new_product_node)
    json.dump(current_catalog, open(PRODUCTS_FILE, "w"), indent=4)
    return jsonify({"success": True, "product": new_product_node}), 201

@app.route("/products/<int:index>", methods=["DELETE"])
@token_required
def remove_inventory_item(index):
    try:
        catalog = json.load(open(PRODUCTS_FILE, "r"))
        catalog.pop(index)
        json.dump(catalog, open(PRODUCTS_FILE, "w"), indent=4)
        return jsonify({"success": True}), 200
    except: return jsonify({"error": "Failed"}), 400

@app.route("/order", methods=["POST"])
def ingest_client_checkout():
    data = request.json or {}
    orders_log = read_stored_orders()
    items = data.get("items", [])
    items_str = "; ".join([f"{i.get('name')} (x{i.get('quantity', 1)})" for i in items]) if isinstance(items, list) else str(items)
        
    order_record = {
        "id": f"SHN-{int(datetime.utcnow().timestamp())}", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "customer": str(data.get("customer", "Guest")), "items": items_str, "total": float(data.get("total", 0.0)), "status": "Pending"
    }
    orders_log.append(order_record)
    write_stored_orders(orders_log)
    return jsonify({"status": "success", "order_id": order_record["id"]}), 201

@app.route("/orders", methods=["GET"])
@token_required
def export_admin_orders(): return jsonify(read_stored_orders()), 200

@app.route("/orders/<string:order_id>", methods=["PATCH"])
@token_required
def mutate_order_state(order_id):
    orders = read_stored_orders()
    for o in orders:
        if o["id"] == order_id:
            o["status"] = request.json.get("status")
            write_stored_orders(orders)
            return jsonify({"success": True}), 200
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
    
