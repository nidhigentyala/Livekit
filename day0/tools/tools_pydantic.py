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
