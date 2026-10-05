"""Part 5 - the four error-handling strategies, code copied from the handout."""
from langchain_core.tools import tool, ToolException
from langgraph.prebuilt import ToolNode


class _FakeDB:
    """Stand-in for the `db` object used in Strategy 3 of the handout."""
    def insert(self, record):
        return None


db = _FakeDB()

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


tools = [divide, find_user, write_to_database]
# Catches all uncaught exceptions from any tool
tool_node = ToolNode(tools, handle_tool_errors=True)

# Or provide a custom error message
tool_node = ToolNode(
    tools,
    handle_tool_errors="The tool failed. Please try a different approach."
)


