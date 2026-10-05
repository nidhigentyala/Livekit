# Intern Handout — Tools & MCP Servers
## Advanced GenAI Agent Training

> **Before you start:** Make sure these packages are installed.
> ```bash
> pip install "langchain[mcp]>=1.4.0" langgraph fastmcp python-dotenv
> ```
> All code here is tested against `langchain>=1.4.0` and `langgraph>=1.1`.

---

## What You Will Learn Today

By the end of this handout you will be able to:

1. Define tools the right way using `@tool`, Pydantic schemas, and `StructuredTool`
2. Use `ToolNode` — LangGraph's built-in tool runner — instead of writing your own loop
3. Give tools access to graph state without showing that data to the LLM
4. Handle tool errors correctly using four different strategies
5. Connect an agent to external tools using MCP — Model Context Protocol
6. Build your own MCP server and expose it over HTTP

Work through each section in order. Run every code example before moving on.

---

## Part 1 — What Is a Tool?

A **tool** is a Python function that an AI agent can call.

The agent (the LLM) cannot run Python directly. Instead, it reads your tool's name and description. It decides *which* tool to call and *what arguments* to pass. Then your code runs the function and sends the result back to the LLM.

Here is the full loop:

```
User question
    ↓
LLM reads tool descriptions
    ↓
LLM decides: "I should call get_weather(city='London')"
    ↓
Your code runs get_weather(city='London')
    ↓
Result goes back to LLM as a ToolMessage
    ↓
LLM writes the final answer for the user
```

The LLM never touches your Python function. It only sees the description and the result.

---

## Part 2 — Three Ways to Define a Tool

### Way 1 — `@tool` decorator (use this most of the time)

Add `@tool` above any function. LangChain reads the function signature and docstring to build a schema. The schema tells the LLM what the tool does and what arguments it needs.

```python
# file: tools_basics.py
from langchain.tools import tool

@tool
def get_exchange_rate(base: str, target: str) -> float:
    """Get the exchange rate between two currencies.

    Args:
        base: The currency to convert FROM. Example: 'USD' or 'EUR'.
        target: The currency to convert TO. Example: 'GBP' or 'JPY'.

    Returns:
        The exchange rate as a number. For example, 1.27 means 1 base = 1.27 target.
    """
    # In a real project, call a currency API here
    rates = {
        "USD_GBP": 0.79,
        "USD_EUR": 0.92,
        "EUR_GBP": 0.86,
    }
    key = f"{base}_{target}"
    if key not in rates:
        raise ValueError(f"No rate found for {base} to {target}")
    return rates[key]


# Check the schema the LLM will see
print("Tool name:", get_exchange_rate.name)
print("Description:", get_exchange_rate.description)
print("Schema:", get_exchange_rate.args_schema.schema())
```

Run this and read the output. Notice that the docstring became the description and the type hints became the schema.

> **Important:** Write clear, specific docstrings. The LLM uses the description to decide *when* to call the tool. A vague description leads to wrong tool choices.

---

### Way 2 — Explicit Pydantic schema (use this when you need field-level validation)

Sometimes you need to add validation rules like "minimum 1 character" or "must be between 1 and 20". Use a Pydantic `BaseModel` for that.

```python
# file: tools_pydantic.py
from pydantic import BaseModel, Field
from langchain.tools import tool

class SearchInput(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="The search query. Be specific for better results."
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return. Between 1 and 20."
    )

@tool(args_schema=SearchInput)
def search_documents(query: str, max_results: int = 5) -> list:
    """Search the internal document store for relevant content."""
    # Real code would call a vector database here
    return [
        {"id": f"doc-{i}", "title": f"Result {i} for '{query}'", "score": 0.9 - i * 0.1}
        for i in range(max_results)
    ]

# Try it — Pydantic will reject invalid input
try:
    search_documents.invoke({"query": "", "max_results": 5})  # empty query
except Exception as e:
    print("Caught error:", e)  # You should see a validation error

result = search_documents.invoke({"query": "vacation policy", "max_results": 2})
print("Results:", result)
```

---

### Way 3 — `StructuredTool.from_function` (use this to wrap existing functions)

If you have an existing function that you cannot or do not want to change, wrap it with `StructuredTool`.

```python
# file: tools_structured.py
from langchain_core.tools import StructuredTool

# This function already exists somewhere in your codebase
def send_notification(channel: str, message: str, urgent: bool = False) -> bool:
    """Existing notification function — we cannot add @tool here."""
    print(f"[{'URGENT ' if urgent else ''}#{channel}] {message}")
    return True

# Wrap it without changing the original function
notify_tool = StructuredTool.from_function(
    func=send_notification,
    name="send_notification",
    description=(
        "Send a message to a team channel. "
        "Use urgent=True only for critical issues that need immediate attention."
    )
)

print("Tool name:", notify_tool.name)
result = notify_tool.invoke({"channel": "engineering", "message": "Deploy complete", "urgent": False})
print("Sent:", result)
```

---

**Which one should I use?**

| Situation | Use |
|---|---|
| New function you are writing now | `@tool` |
| Need strict field validation or richer descriptions | `@tool(args_schema=MyModel)` |
| Wrapping an existing function you cannot modify | `StructuredTool.from_function` |

📖 **Read more:** [LangChain Tools guide](https://docs.langchain.com/oss/python/langchain/tools)

---

## Part 3 — `ToolNode`: The Right Way to Run Tools

Until now, you may have written a `call_tools` function by hand — a loop that reads `tool_calls` from the last message and runs each tool. `ToolNode` does all of that for you.

**What `ToolNode` gives you:**
- Runs multiple tool calls at the same time (parallel execution)
- Wraps each result in the correct `ToolMessage` format automatically
- Handles errors so the agent does not crash
- Supports `InjectedState` (you will learn this in Part 4)

### Without `ToolNode` — the old hand-rolled way

```python
# OLD WAY — you had to write this yourself
def call_tools(state):
    last_message = state["messages"][-1]
    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool_fn = tools_by_name[tool_call["name"]]
        result = tool_fn.invoke(tool_call["args"])
        from langchain_core.messages import ToolMessage
        tool_messages.append(
            ToolMessage(content=str(result), tool_call_id=tool_call["id"])
        )
    return {"messages": tool_messages}
```

### With `ToolNode` — the current correct way

```python
# file: toolnode_example.py
from langchain.tools import tool
from langchain_openai import ChatOpenAI
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
llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(tools)

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
```

Run this. The agent should answer both questions in one response. Notice you did not write any tool execution loop.

📖 **Read more:** [ToolNode reference](https://docs.langchain.com/oss/python/langgraph/workflows-agents#toolnode)

---

## Part 4 — Giving Tools Access to Graph State

Sometimes a tool needs information from your agent's state — like the current user's ID or their permission level. But you do not want the LLM to decide or invent that information. You want it to come from state automatically.

`InjectedState` solves this. It injects a field from state into the tool, but **hides it from the LLM schema**. The LLM never sees it and never tries to fill it.

```python
# file: injected_state_example.py
from langchain.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()

# --- State includes user info ---
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str                    # Set when the user logs in
    user_role: str                  # Set from your database

# --- Tool uses injected state ---
@tool
def get_my_profile(
    fields: list,
    # This argument is injected from state — the LLM cannot see it
    user_id: Annotated[str, InjectedState("user_id")]
) -> dict:
    """Get profile information for the current logged-in user.

    Args:
        fields: List of profile fields to return. For example: ['name', 'email'].
    """
    # In a real project, query your database here
    profiles = {
        "alice": {"name": "Alice Smith", "email": "alice@company.com", "dept": "Engineering"},
        "bob":   {"name": "Bob Jones",  "email": "bob@company.com",  "dept": "Finance"},
    }
    profile = profiles.get(user_id, {})
    return {k: profile.get(k, "Not found") for k in fields}

@tool
def list_reports(
    # InjectedState injects user_role — LLM does not see this argument
    user_role: Annotated[str, InjectedState("user_role")]
) -> list:
    """List the reports available to the current user."""
    if user_role == "admin":
        return ["Sales Report", "HR Report", "Finance Report", "Security Report"]
    else:
        return ["Sales Report"]  # Regular users see fewer reports

# --- Verify the LLM schema does NOT include injected fields ---
print("get_my_profile schema:")
print(get_my_profile.args_schema.schema())
# You should see 'fields' but NOT 'user_id' in the properties

print("\nlist_reports schema:")
print(list_reports.args_schema.schema())
# You should see an EMPTY properties dict — no 'user_role'

# --- Build the agent ---
tools = [get_my_profile, list_reports]
llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(tools)
tool_node = ToolNode(tools)

def call_model(state: AgentState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}

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

# --- Run as Alice (admin) ---
print("\n=== Alice (admin) ===")
result = graph.invoke({
    "messages": [HumanMessage(content="What reports can I see?")],
    "user_id": "alice",
    "user_role": "admin"
})
print(result["messages"][-1].content)

# --- Run as Bob (regular user) ---
print("\n=== Bob (viewer) ===")
result = graph.invoke({
    "messages": [HumanMessage(content="What reports can I see?")],
    "user_id": "bob",
    "user_role": "viewer"
})
print(result["messages"][-1].content)
```

Alice should see 4 reports. Bob should see 1. The LLM never knew about `user_role` — it came from state automatically.

---

## Part 5 — Handling Tool Errors

Not every tool call works correctly. You need to decide what to do when something goes wrong. There are four different strategies — use the right one for each situation.

### Strategy 1 — `ToolException` (let the LLM try again)

Use this when the problem is something the LLM can fix by sending different arguments.

```python
from langchain_core.tools import tool, ToolException

@tool
def divide(a: float, b: float) -> float:
    """Divide a by b.

    Args:
        a: The number to divide.
        b: The number to divide by. Must not be zero.
    """
    if b == 0:
        # ToolException makes the error text visible to the LLM as a ToolMessage
        # The LLM can read it and try a different approach
        raise ToolException(
            "Cannot divide by zero. Please provide a non-zero value for b and try again."
        )
    return a / b
```

The LLM receives the error message as a `ToolMessage`. It can then try different arguments or explain the problem to the user.

---

### Strategy 2 — Return a soft string (hide the error from the LLM)

Use this when the tool has a known failure case that should produce a polite message, not an error.

```python
@tool
def find_user(user_id: str) -> str:
    """Look up a user by their ID.

    Args:
        user_id: The user's unique ID.
    """
    users = {"u001": "Alice Smith", "u002": "Bob Jones"}
    user = users.get(user_id)

    if user is None:
        # Return a soft message — the LLM will tell the user politely
        # The agent does NOT crash and the LLM is NOT confused
        return f"No user found with ID '{user_id}'. Please check the ID and try again."

    return user
```

---

### Strategy 3 — Let unexpected errors bubble up (do not hide bugs)

If something crashes that you did not expect, do **not** catch the exception silently. Let it surface so you can debug it.

```python
@tool
def write_to_database(record: dict) -> str:
    """Write a record to the production database.

    Args:
        record: The data to save.
    """
    # Do NOT add a try/except here unless you know how to handle the error
    # If the database is down, the crash tells you — do not swallow it quietly
    db.insert(record)
    return "Record saved."
```

---

### Strategy 4 — `handle_tool_errors=True` on `ToolNode` (safety net)

This is a safety net. `ToolNode` catches any uncaught exception from any tool and converts it to a `ToolMessage` automatically. The agent does not crash.

```python
# Catches all uncaught exceptions from any tool
tool_node = ToolNode(tools, handle_tool_errors=True)

# Or provide a custom error message
tool_node = ToolNode(
    tools,
    handle_tool_errors="The tool failed. Please try a different approach."
)
```

**Quick reference:**

| Situation | Use |
|---|---|
| LLM sent bad arguments — it can fix this | `ToolException` (Strategy 1) |
| Known soft failure — hide from LLM | Return a string message (Strategy 2) |
| Unexpected crash — needs debugging | Let it bubble up (Strategy 3) |
| Safety net for all tools at once | `ToolNode(handle_tool_errors=True)` (Strategy 4) |

---

### Practice Exercise — Error Handling (30 min)

Create `exercise_errors.py`. Define these three tools and build an agent with `ToolNode`:

1. `get_stock_price(ticker: str) -> float` — return a price from a small hardcoded dict. Raise `ToolException` if the ticker is not found.
2. `calculate_gain(buy_price: float, sell_price: float) -> float` — return the profit. If `sell_price < buy_price`, return a soft message string like "This would be a loss, not a gain."
3. `send_report(email: str) -> bool` — always returns `True`. (Leave any exception to bubble up.)

Test with:
- A valid ticker
- An unknown ticker — does the LLM respond sensibly?
- A sell price lower than buy price — does the LLM understand the soft message?

---

## Part 6 — What Is MCP?

**MCP** stands for **Model Context Protocol**.

Think of it like a USB standard. Before USB, every device used a different cable. After USB, one standard connector works for everything. MCP does the same for AI tools — it defines one standard way for an agent to connect to external services.

```
Without MCP:
  Agent ─── custom code ──→ Your Database
  Agent ─── custom code ──→ Slack
  Agent ─── custom code ──→ GitHub
  (You write 3 different integrations)

With MCP:
  Agent ─── MCPAdapter ──→ MCP Server
                               ├──→ Database tools
                               ├──→ Slack tools
                               └──→ GitHub tools
  (One pattern for everything)
```

An MCP server exposes tools over a network connection. Your agent connects to the server, asks what tools are available, and gets them back as standard LangChain tools.

### Connection types

| Type | When to use | Example |
|---|---|---|
| HTTP URL | Remote server (production) | `"url": "https://myserver.com/mcp"` |
| File path | Local Python script (development) | `Path("my_server.py")` |
| In-process | Testing (no network needed) | Pass the FastMCP object directly |

---

## Part 7 — Connecting to an MCP Server

The current API uses `MCPAdapter` from `langchain.mcp`. It is an **async context manager** — you open it with `async with`, use it, and it closes cleanly when done.

### Install

```bash
pip install "langchain[mcp]>=1.4.0"
```

### Connect to one server

```python
# file: mcp_connect_one.py
import asyncio
from langchain.mcp import MCPAdapter
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

async def main():
    # Connect to the real LangChain docs MCP server
    # This is a live public server you can test against right now
    async with MCPAdapter("https://docs.langchain.com/mcp") as adapter:

        # Discover all tools the server offers
        tools = await adapter.list_tools()

        print(f"Found {len(tools)} tools:")
        for t in tools:
            print(f"  - {t.name}: {t.description[:70]}")

        # Use the tools exactly like any other LangChain tool
        llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(tools)
        tool_node = ToolNode(tools)

        def call_model(state: AgentState) -> dict:
            return {"messages": [llm.invoke(state["messages"])]}

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

        # Ask a question that requires the server's tools
        result = graph.invoke({
            "messages": [HumanMessage(content="What is LangGraph's ToolNode?")]
        })
        print("\nAnswer:", result["messages"][-1].content)

asyncio.run(main())
```

### Connect to multiple servers

```python
# file: mcp_connect_multi.py
import asyncio
from langchain.mcp import MCPAdapter

async def main():
    config = {
        "mcpServers": {
            # Server 1: remote HTTP
            "langchain_docs": {
                "url": "https://docs.langchain.com/mcp"
            },
            # Server 2: local Python script
            # "my_local_server": Path("hr_server.py"),
        }
    }

    async with MCPAdapter(config) as adapter:
        tools = await adapter.list_tools()
        print(f"Total tools from all servers: {len(tools)}")

asyncio.run(main())
```

> **Note:** The old `MultiServerMCPClient` is replaced by `MCPAdapter`. If you see old tutorials using `MultiServerMCPClient`, use `MCPAdapter` instead.

📖 **Read more:** [LangChain MCP Guide](https://docs.langchain.com/oss/python/langchain/mcp) and [Migration guide](https://docs.langchain.com/oss/python/migrate/langchain-mcp-adapters)

---

### Practice Exercise — Connect to a Live MCP Server (30 min)

Create `exercise_mcp_connect.py`. Connect to `https://docs.langchain.com/mcp` using `MCPAdapter`. Build a full agent that uses the tools from that server.

Ask these two questions:
1. "How do I use `interrupt()` in LangGraph?"
2. "What is `subgraphs=True` used for in streaming?"

In comments at the top of the file, answer:
- How many tools did the server expose?
- Which tool name was called for each question?

---

## Part 8 — Building Your Own MCP Server

You can build your own MCP server and expose your internal tools over HTTP. Any agent can then connect to it — yours, a colleague's, or a client's.

Use **`fastmcp`** — a Python library that makes building servers simple.

```bash
pip install fastmcp
```

### A complete MCP server

```python
# file: my_mcp_server.py
from fastmcp import FastMCP

# Create the server with a name and description
mcp = FastMCP(
    name="HR Tools Server",
    description="Internal HR tools exposed via MCP"
)

# Define tools using @mcp.tool() — similar to @tool from LangChain
@mcp.tool()
def get_employee(employee_id: str) -> dict:
    """Look up an employee by their ID.

    Args:
        employee_id: The employee's unique ID. Example: 'EMP-001'.

    Returns:
        Employee record with name, department, manager, and leave balance.
    """
    employees = {
        "EMP-001": {
            "name": "Priya Sharma",
            "department": "Engineering",
            "manager": "Raj Kumar",
            "annual_leave_remaining": 12
        },
        "EMP-002": {
            "name": "David Chen",
            "department": "Finance",
            "manager": "Sarah Lee",
            "annual_leave_remaining": 8
        },
    }
    employee = employees.get(employee_id)
    if not employee:
        return {"error": f"No employee found with ID '{employee_id}'"}
    return employee

@mcp.tool()
def check_leave_balance(employee_id: str, leave_type: str = "annual") -> dict:
    """Check the leave balance for an employee.

    Args:
        employee_id: The employee's unique ID.
        leave_type: Type of leave to check. Options: 'annual', 'sick', 'personal'.

    Returns:
        Leave balance details including days remaining and days used.
    """
    balances = {
        "EMP-001": {"annual": 12, "sick": 7, "personal": 2},
        "EMP-002": {"annual": 8,  "sick": 10, "personal": 3},
    }
    emp_balance = balances.get(employee_id)
    if not emp_balance:
        return {"error": f"Employee '{employee_id}' not found"}

    days_remaining = emp_balance.get(leave_type, 0)
    return {
        "employee_id": employee_id,
        "leave_type": leave_type,
        "days_remaining": days_remaining,
        "total_days": 20 if leave_type == "annual" else 10
    }

@mcp.tool()
def request_leave(
    employee_id: str,
    leave_type: str,
    days: int,
    reason: str
) -> dict:
    """Submit a leave request for an employee.

    Args:
        employee_id: The employee's unique ID.
        leave_type: Type of leave: 'annual', 'sick', or 'personal'.
        days: Number of days requested. Must be positive.
        reason: Brief reason for the leave request.

    Returns:
        Request confirmation with a request ID and approval status.
    """
    import uuid
    if days <= 0:
        return {"error": "Days must be a positive number"}

    request_id = f"LR-{uuid.uuid4().hex[:6].upper()}"
    # Requests of 2 days or less are auto-approved
    status = "approved" if days <= 2 else "pending_manager_approval"

    return {
        "request_id": request_id,
        "employee_id": employee_id,
        "leave_type": leave_type,
        "days_requested": days,
        "status": status,
        "message": f"Request {request_id} submitted. Status: {status}"
    }

# --- Run the server ---
if __name__ == "__main__":
    print("Starting HR Tools MCP Server on http://localhost:8001/mcp")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001, path="/mcp")
```

Start the server in one terminal:
```bash
python my_mcp_server.py
```

### Connect an agent to your server

```python
# file: use_my_server.py
import asyncio
from langchain.mcp import MCPAdapter
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

async def main():
    # Connect to your local server
    async with MCPAdapter("http://localhost:8001/mcp") as adapter:
        tools = await adapter.list_tools()

        print(f"Your server exposed {len(tools)} tools:")
        for t in tools:
            print(f"  - {t.name}")

        llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(tools)
        tool_node = ToolNode(tools)

        def call_model(state: AgentState) -> dict:
            return {"messages": [llm.invoke(state["messages"])]}

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

        # Test your server
        questions = [
            "Look up employee EMP-001. What is their annual leave balance?",
            "Request 1 day of sick leave for EMP-002 because they have a doctor's appointment.",
        ]

        for q in questions:
            print(f"\nQ: {q}")
            result = graph.invoke({"messages": [HumanMessage(content=q)]})
            print(f"A: {result['messages'][-1].content}")

asyncio.run(main())
```

Run this in a second terminal (while the server is running). Confirm the agent uses your server's tools correctly.

📖 **Read more:** [fastmcp documentation](https://gofastmcp.com)

---

## End-of-Day Test Task (Work independently — no help allowed)

**Time allowed: 60 minutes**

### Task: Inventory Agent with Tools and MCP

You will build two things separately, then combine them.

---

**Part A — Custom Tools with `ToolNode` (30 min)**

Create `test_task_tools.py`.

Define these 4 tools:

1. `check_stock(sku: str) -> dict` — return the stock level for a SKU from this hardcoded data:
   ```python
   stock = {
       "SKU-001": {"name": "Widget A", "quantity": 150, "warehouse": "WH-North"},
       "SKU-002": {"name": "Widget B", "quantity": 12,  "warehouse": "WH-South"},
       "SKU-003": {"name": "Gadget X", "quantity": 0,   "warehouse": "WH-North"},
   }
   ```
   If the SKU is not found, raise `ToolException` with a clear message.

2. `place_order(sku: str, quantity: int) -> dict` — accept an order. If `quantity > 500`, raise `ToolException` saying the maximum order is 500 units. Otherwise return a confirmation dict with a fake order ID.

3. `get_low_stock_report() -> list` — return a list of SKUs where quantity is less than 20. No arguments needed. Return the list of dicts.

4. `calculate_restock_cost(sku: str, units_to_order: int, unit_cost: float) -> float` — return `units_to_order * unit_cost`. If either number is negative, return the soft string `"Invalid input: all values must be positive."` (do not raise an error).

Build a `ToolNode`-based agent and test with these questions:
- "What is the stock level for SKU-002?"
- "I want to order 600 units of SKU-001" (should trigger `ToolException`)
- "Show me all low stock items"
- "How much will it cost to order -5 units at £10 each?" (should return the soft message)

---

**Part B — MCP Server (30 min)**

Create `test_task_server.py` (the server) and `test_task_client.py` (the consuming agent).

**In `test_task_server.py`**, build an MCP server on port `8002` with these 2 tools:

1. `get_supplier(supplier_id: str) -> dict` — return supplier info from a hardcoded dict (3 suppliers minimum).
2. `request_quote(supplier_id: str, sku: str, quantity: int) -> dict` — return a fake quote with price and lead time. Reject unknown suppliers with an error message in the return dict (not an exception).

**In `test_task_client.py`**, connect to `http://localhost:8002/mcp` and build an agent that answers:
- "Get the details for supplier SUP-001"
- "Request a quote for 100 units of SKU-001 from supplier SUP-002"

---

**Checklist before you submit:**

- [ ] `check_stock` raises `ToolException` for unknown SKUs — agent responds sensibly
- [ ] `place_order(quantity=600)` raises `ToolException` — agent explains the limit
- [ ] `calculate_restock_cost` with negative values returns a soft string (no crash)
- [ ] MCP server starts on port 8002 without error
- [ ] Client agent discovers tools from the server and uses them correctly
- [ ] You can print `tool.args_schema.schema()` for any tool and it looks correct

---

## Summary — What You Learned Today

| Concept | What it does |
|---|---|
| `@tool` | Turns a Python function into a tool the LLM can call |
| `args_schema` | Adds Pydantic validation to your tool's inputs |
| `StructuredTool.from_function` | Wraps an existing function without changing it |
| `ToolNode` | LangGraph's built-in tool runner — replaces hand-written loops |
| `InjectedState` | Passes state data into a tool without exposing it to the LLM |
| `ToolException` | Sends an error message to the LLM so it can try again |
| Soft string return | Returns a polite message instead of raising an error |
| MCP | Open standard for connecting agents to external tool servers |
| `MCPAdapter` | Connects your agent to one or more MCP servers |
| `fastmcp` | Python library for building MCP servers quickly |

---

## External Resources

| Topic | Link |
|---|---|
| LangChain Tools full guide | https://docs.langchain.com/oss/python/langchain/tools |
| ToolNode reference | https://docs.langchain.com/oss/python/langgraph/workflows-agents#toolnode |
| LangChain MCP guide | https://docs.langchain.com/oss/python/langchain/mcp |
| MCPAdapter migration guide | https://docs.langchain.com/oss/python/migrate/langchain-mcp-adapters |
| fastmcp documentation | https://gofastmcp.com |

---

*Tools & MCP Servers Handout — Advanced GenAI Agent Training*
*Verified against langchain>=1.4.0 and langgraph>=1.1 — June 2026*
