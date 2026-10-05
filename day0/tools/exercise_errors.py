"""
Practice Exercise — Error handling (Part 5).

Run:
    python tools/exercise_errors.py
"""
import asyncio
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

PRICES = {"AAPL": 227.50, "MSFT": 415.20, "GOOGL": 168.90}


@tool
def get_stock_price(ticker: str) -> float:
    """Get the current price of a stock.

    Args:
        ticker: Stock ticker symbol. Example: 'AAPL'.
    """
    price = PRICES.get(ticker.upper())
    if price is None:
        raise ToolException(
            f"Ticker '{ticker}' not found. Available tickers: {', '.join(PRICES)}."
        )
    return price


@tool
def calculate_gain(buy_price: float, sell_price: float) -> float | str:
    """Calculate profit from buying and selling a stock.

    Args:
        buy_price: Price paid per share.
        sell_price: Price sold at per share.
    """
    if sell_price < buy_price:
        return "This would be a loss, not a gain."
    return sell_price - buy_price


@tool
def send_report(email: str) -> bool:
    """Send the stock report to an email address.

    Args:
        email: Recipient email address.
    """
    # No try/except on purpose: unexpected errors should bubble up.
    return True


tools = [get_stock_price, calculate_gain, send_report]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def build_graph():
    llm = ChatGroq(model="openai/gpt-oss-20b").bind_tools(tools)

    async def call_model(state: AgentState) -> dict:
        return {"messages": [await llm.ainvoke(state["messages"])]}

    def should_continue(state: AgentState) -> str:
        return "tools" if getattr(state["messages"][-1], "tool_calls", None) else END

    b = StateGraph(AgentState)
    b.add_node("agent", call_model)
    b.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    b.set_entry_point("agent")
    b.add_conditional_edges("agent", should_continue)
    b.add_edge("tools", "agent")
    return b.compile()


async def main():
    graph = build_graph()
    for q in [
        "What is the price of AAPL?",                                   # valid ticker
        "What is the price of ZZZZ?",                                   # ToolException
        "I bought at 100 and sold at 80. What is my gain?",             # soft message
    ]:
        print(f"\nQ: {q}")
        result = await graph.ainvoke({"messages": [HumanMessage(content=q)]})
        print(f"A: {result['messages'][-1].content}")


if __name__ == "__main__":
    asyncio.run(main())
