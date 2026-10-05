"""
End-of-Day Test — Part B (client): agent that consumes the supplier MCP server.

Start the server first (separate terminal):
    python tools/test_task_server.py
Then run:
    python tools/test_task_client.py
"""
import asyncio
from typing import Annotated

from dotenv import load_dotenv
from langchain.mcp import MCPAdapter
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

load_dotenv()

SERVER_URL = "http://localhost:8002/mcp"


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


QUESTIONS = [
    "Get the details for supplier SUP-001",
    "Request a quote for 100 units of SKU-001 from supplier SUP-002",
]


async def main():
    async with MCPAdapter(SERVER_URL) as adapter:
        tools = await adapter.list_tools()

        print(f"Server exposed {len(tools)} tools:")
        for t in tools:
            print(f"  - {t.name}")
            print(f"    schema: {t.args_schema}")

        llm = ChatGroq(model="openai/gpt-oss-20b").bind_tools(tools)

        async def call_model(state: AgentState) -> dict:
            return {"messages": [await llm.ainvoke(state["messages"])]}

        def should_continue(state: AgentState) -> str:
            last = state["messages"][-1]
            return "tools" if getattr(last, "tool_calls", None) else END

        builder = StateGraph(AgentState)
        builder.add_node("agent", call_model)
        builder.add_node("tools", ToolNode(tools, handle_tool_errors=True))
        builder.set_entry_point("agent")
        builder.add_conditional_edges("agent", should_continue)
        builder.add_edge("tools", "agent")
        graph = builder.compile()

        for q in QUESTIONS:
            print(f"\nQ: {q}")
            result = await graph.ainvoke({"messages": [HumanMessage(content=q)]})
            print(f"A: {result['messages'][-1].content}")


if __name__ == "__main__":
    asyncio.run(main())
