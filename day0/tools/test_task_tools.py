"""
End-of-Day Test — Part A: Inventory tools + ToolNode agent.

Run:
    python tools/test_task_tools.py
Requires OPENAI_API_KEY in .env
"""
import asyncio
import uuid
from typing import Annotated

from dotenv import load_dotenv
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_core.tools import ToolException
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

load_dotenv()

# --------------------------------------------------------------------------
# Hardcoded inventory data
# --------------------------------------------------------------------------
STOCK = {
    "SKU-001": {"name": "Widget A", "quantity": 150, "warehouse": "WH-North"},
    "SKU-002": {"name": "Widget B", "quantity": 12, "warehouse": "WH-South"},
    "SKU-003": {"name": "Gadget X", "quantity": 0, "warehouse": "WH-North"},
}

MAX_ORDER_QUANTITY = 500
LOW_STOCK_THRESHOLD = 20


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------
@tool
def check_stock(sku: str) -> dict:
    """Check the current stock level for a single product SKU.

    Args:
        sku: The product SKU code. Example: 'SKU-001'.

    Returns:
        A dict with the product name, quantity in stock and warehouse.
    """
    item = STOCK.get(sku)
    if item is None:
        # LLM can fix this (e.g. correct the SKU or tell the user)
        raise ToolException(
            f"SKU '{sku}' was not found. Valid SKUs are: {', '.join(STOCK)}."
        )
    return {"sku": sku, **item}


@tool
def place_order(sku: str, quantity: int) -> dict:
    """Place a purchase order for a product SKU.

    Args:
        sku: The product SKU code. Example: 'SKU-001'.
        quantity: Number of units to order. Maximum 500 per order.

    Returns:
        An order confirmation with an order ID.
    """
    if quantity > MAX_ORDER_QUANTITY:
        raise ToolException(
            f"Maximum order is {MAX_ORDER_QUANTITY} units per order. "
            f"You requested {quantity}. Please order {MAX_ORDER_QUANTITY} or fewer."
        )
    return {
        "order_id": f"ORD-{uuid.uuid4().hex[:8].upper()}",
        "sku": sku,
        "quantity": quantity,
        "status": "confirmed",
    }


@tool
def get_low_stock_report() -> list:
    """List every SKU whose stock quantity is below 20 units. Takes no arguments."""
    return [
        {"sku": sku, **item}
        for sku, item in STOCK.items()
        if item["quantity"] < LOW_STOCK_THRESHOLD
    ]


@tool
def calculate_restock_cost(sku: str, units_to_order: int, unit_cost: float) -> float | str:
    """Calculate the total cost of restocking a SKU.

    Args:
        sku: The product SKU code. Example: 'SKU-002'.
        units_to_order: Number of units to order. Must not be negative.
        unit_cost: Cost per unit. Must not be negative.

    Returns:
        The total cost (units_to_order * unit_cost), or a message if input is invalid.
    """
    if units_to_order < 0 or unit_cost < 0:
        # Soft failure: return a polite string instead of raising
        return "Invalid input: all values must be positive."
    return units_to_order * unit_cost


tools = [check_stock, place_order, get_low_stock_report, calculate_restock_cost]


# --------------------------------------------------------------------------
# Agent (ToolNode based)
# --------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def build_graph():
    llm = ChatGroq(model="openai/gpt-oss-20b").bind_tools(tools)

    async def call_model(state: AgentState) -> dict:
        return {"messages": [await llm.ainvoke(state["messages"])]}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    builder = StateGraph(AgentState)
    builder.add_node("agent", call_model)
    # handle_tool_errors=True -> ToolException becomes a ToolMessage the LLM can read
    builder.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    builder.set_entry_point("agent")
    builder.add_conditional_edges("agent", should_continue)
    builder.add_edge("tools", "agent")
    return builder.compile()


QUESTIONS = [
    "What is the stock level for SKU-002?",
    "I want to order 600 units of SKU-001",            # -> ToolException
    "Show me all low stock items",
    "How much will it cost to order -5 units at £10 each?",  # -> soft string
]


async def main():
    # Checklist item: args_schema must look correct for every tool
    for t in tools:
        print(f"[schema] {t.name}: {t.args_schema.schema()}")

    graph = build_graph()
    for q in QUESTIONS:
        print(f"\nQ: {q}")
        result = await graph.ainvoke({"messages": [HumanMessage(content=q)]})
        print(f"A: {result['messages'][-1].content}")


if __name__ == "__main__":
    asyncio.run(main())
