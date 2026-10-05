# file: toolnode_example.py
from langchain.tools import tool
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv

load_dotenv()

# --- Define tools ---
@tool
def add(a: float, b: float) -> float:
    """Add two numbers together. Args: a (float), b (float)."""
    return a + b

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together. Args: a (float), b (float)."""
    return a * b

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city. Args: city (str)."""
    # Fake data for practice
    weather = {"London": "15°C, cloudy", "Paris": "22°C, sunny", "Tokyo": "28°C, humid"}
    return weather.get(city, f"No weather data for {city}")

tools = [add, multiply, get_weather]

# --- LLM + state ---
llm = ChatGroq(model="openai/gpt-oss-20b").bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# --- Nodes ---
def call_model(state: AgentState) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END

# --- Build graph ---
# ToolNode replaces the hand-rolled call_tools function
tool_node = ToolNode(tools)

builder = StateGraph(AgentState)
builder.add_node("agent", call_model)
builder.add_node("tools", tool_node)   # One line — no loop needed
builder.set_entry_point("agent")
builder.add_conditional_edges("agent", should_continue)
builder.add_edge("tools", "agent")
graph = builder.compile()

# --- Run ---
result = graph.invoke({
    "messages": [HumanMessage(content="What is 15 multiplied by 8? Also, what is the weather in London?")]
})
print(result["messages"][-1].content)
