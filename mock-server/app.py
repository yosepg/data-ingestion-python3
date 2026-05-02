"""
Mock Customer Data Server
Flask API that serves customer data from a JSON file with pagination support.
"""

import json
import os
from flask import Flask, jsonify, request, abort

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Load customer data from JSON file at startup
# ---------------------------------------------------------------------------
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "customers.json")

def load_customers() -> list[dict]:
    """Load and return customer records from the JSON data file."""
    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


CUSTOMERS: list[dict] = load_customers()
CUSTOMER_INDEX: dict[str, dict] = {c["customer_id"]: c for c in CUSTOMERS}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "mock-server",
        "total_customers": len(CUSTOMERS),
    }), 200


@app.route("/api/customers", methods=["GET"])
def get_customers():
    """
    Return a paginated list of customers.

    Query params:
        page  (int, default 1)   – 1-based page number
        limit (int, default 10)  – records per page (max 100)
    """
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
    except ValueError:
        return jsonify({"error": "'page' and 'limit' must be integers"}), 400

    if page < 1:
        return jsonify({"error": "'page' must be >= 1"}), 400
    if limit < 1 or limit > 100:
        return jsonify({"error": "'limit' must be between 1 and 100"}), 400

    total = len(CUSTOMERS)
    start = (page - 1) * limit
    end = start + limit
    page_data = CUSTOMERS[start:end]

    return jsonify({
        "data": page_data,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
    }), 200


@app.route("/api/customers/<string:customer_id>", methods=["GET"])
def get_customer(customer_id: str):
    """Return a single customer by ID, or 404 if not found."""
    customer = CUSTOMER_INDEX.get(customer_id)
    if customer is None:
        abort(404, description=f"Customer '{customer_id}' not found.")
    return jsonify({"data": customer}), 200


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": str(error.description)}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
