from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import csv
import os

app = Flask(__name__)
CORS(app)

ORDERS_FILE = "orders.csv"

# Ensure file exists
if not os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, "w", newline="") as f:
        pass

# Save order
def save_order(data):
    with open(ORDERS_FILE, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("product")
        ])

# Read orders
def read_orders():
    orders = []
    try:
        with open(ORDERS_FILE, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) >= 2:
                    orders.append({
                        "time": row[0],
                        "product": row[1]
                    })
    except:
        pass
    return orders

# API: receive order
@app.route("/order", methods=["POST"])
def receive_order():
    data = request.json
    save_order(data)
    return jsonify({"status": "success"})

# API: send orders to dashboard
@app.route("/orders", methods=["GET"])
def get_orders():
    return jsonify(read_orders())

# Health check (important for Render)
@app.route("/")
def home():
    return "Backend is running"

if __name__ == "__main__":
    app.run()
