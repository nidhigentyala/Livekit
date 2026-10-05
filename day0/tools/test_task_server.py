"""
End-of-Day Test — Part B (server): Supplier MCP server on port 8002.

Run:
    python tools/test_task_server.py
Endpoint: http://localhost:8002/mcp
"""
from fastmcp import FastMCP

mcp = FastMCP(
    name="Supplier Tools Server",
    instructions="Supplier lookup and quote tools exposed via MCP.",
)

SUPPLIERS = {
    "SUP-001": {
        "name": "Acme Components Ltd",
        "country": "UK",
        "contact_email": "sales@acme-components.example",
        "rating": 4.6,
    },
    "SUP-002": {
        "name": "Globex Supplies",
        "country": "Germany",
        "contact_email": "orders@globex.example",
        "rating": 4.2,
    },
    "SUP-003": {
        "name": "Initech Wholesale",
        "country": "India",
        "contact_email": "quotes@initech.example",
        "rating": 3.9,
    },
}

# Fake per-supplier pricing: (unit price in GBP, lead time in days)
PRICING = {
    "SUP-001": (9.50, 5),
    "SUP-002": (8.75, 10),
    "SUP-003": (7.90, 14),
}


@mcp.tool()
def get_supplier(supplier_id: str) -> dict:
    """Look up a supplier by ID.

    Args:
        supplier_id: The supplier's unique ID. Example: 'SUP-001'.

    Returns:
        Supplier details (name, country, contact email, rating), or an error message.
    """
    supplier = SUPPLIERS.get(supplier_id)
    if not supplier:
        return {"error": f"No supplier found with ID '{supplier_id}'"}
    return {"supplier_id": supplier_id, **supplier}


@mcp.tool()
def request_quote(supplier_id: str, sku: str, quantity: int) -> dict:
    """Request a price quote from a supplier for a SKU.

    Args:
        supplier_id: The supplier's unique ID. Example: 'SUP-002'.
        sku: The product SKU code. Example: 'SKU-001'.
        quantity: Number of units to quote. Must be positive.

    Returns:
        A quote with unit price, total price and lead time, or an error message.
    """
    if supplier_id not in SUPPLIERS:
        return {"error": f"Unknown supplier '{supplier_id}'. Cannot request a quote."}
    if quantity <= 0:
        return {"error": "Quantity must be a positive number."}

    unit_price, lead_time_days = PRICING[supplier_id]
    return {
        "supplier_id": supplier_id,
        "supplier_name": SUPPLIERS[supplier_id]["name"],
        "sku": sku,
        "quantity": quantity,
        "unit_price_gbp": unit_price,
        "total_price_gbp": round(unit_price * quantity, 2),
        "lead_time_days": lead_time_days,
    }


if __name__ == "__main__":
    print("Starting Supplier MCP Server on http://localhost:8002/mcp")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8002, path="/mcp")
