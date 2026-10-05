import asyncio
from typing import Annotated

from dotenv import load_dotenv
from langchain.mcp import MCPAdapter
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

async def main():
    async with MCPAdapter("https://docs.langchain.com/mcp") as adapter:

        all_tools = await adapter.list_tools()
        print(f"Found {len(all_tools)} tools:")
        for t in all_tools:
            print(f"  - {t.name}: {t.description[:70]}")

        raw_search_tool = next(t for t in all_tools if t.name == "search_docs_by_lang_chain")

        @tool
        async def search_docs(query: str) -> str:
            """Search the LangChain documentation for relevant information.

            Args:
                query: What to search for. Example: 'ToolNode usage'.
            """
            result = await raw_search_tool.ainvoke({"query": query})
            # Raw search results return several full doc pages — far past
            # Groq's free-tier TPM cap. Cap it before it goes back to the LLM.
            return str(result)[:2000]

        tools = [search_docs]

        llm = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0,
            reasoning_effort="low",
            max_tokens=500,
        ).bind_tools(tools)
        tool_node = ToolNode(tools, handle_tool_errors=True)

        async def call_model(state: AgentState) -> dict:
            return {"messages": [await llm.ainvoke(state["messages"])]}

        def should_continue(state: AgentState) -> str:
            last = state["messages"][-1]
            return "tools" if (hasattr(last, "tool_calls") and last.tool_calls) else END

        builder = StateGraph(AgentState)
        builder.add_node("agent", call_model)
        builder.add_node("tools", tool_node)
        builder.set_entry_point("agent")
        builder.add_conditional_edges("agent", should_continue)
        builder.add_edge("tools", "agent")
        graph = builder.compile()

        result = await graph.ainvoke({
            "messages": [HumanMessage(content="What is LangGraph's ToolNode?")]
        })
        print("\nAnswer:", result["messages"][-1].content)

asyncio.run(main())