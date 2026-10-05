import asyncio
from typing import Annotated

from dotenv import load_dotenv
from langchain.mcp import MCPAdapter
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


QUESTIONS = [
    "How do I use `interrupt()` in LangGraph?",
    "What is `subgraphs=True` used for in streaming?",
]


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
                query: What to search for. Example: 'interrupt function usage'.
            """
            result = await raw_search_tool.ainvoke({"query": query})
            text = str(result)
            print(f"[debug] raw search result length: {len(text)} chars")
            # The server returns several full doc pages with every code
            # sample — that, not the tool schema, was the real source of
            # the oversized requests. Cap it hard.
            return text[:2000]

        tools = [search_docs]

        llm = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0,
            reasoning_effort="low",
            max_tokens=500,
        ).bind_tools(tools)

        async def call_model(state: AgentState) -> dict:
            try:
                response = await llm.ainvoke(state["messages"])
            except Exception as e:
                print(f"[warning] call failed, retrying once: {e}")
                response = await llm.ainvoke(state["messages"])
            return {"messages": [response]}

        def should_continue(state: AgentState) -> str:
            return "tools" if getattr(state["messages"][-1], "tool_calls", None) else END

        b = StateGraph(AgentState)
        b.add_node("agent", call_model)
        b.add_node("tools", ToolNode(tools, handle_tool_errors=True))
        b.set_entry_point("agent")
        b.add_conditional_edges("agent", should_continue)
        b.add_edge("tools", "agent")
        graph = b.compile()

        for q in QUESTIONS:
            print(f"\nQ: {q}")
            result = await graph.ainvoke({"messages": [HumanMessage(content=q)]})
            for m in result["messages"]:
                for call in getattr(m, "tool_calls", None) or []:
                    print(f"[tool call] {call['name']}")
            print(f"A: {result['messages'][-1].content}")


if __name__ == "__main__":
    asyncio.run(main())