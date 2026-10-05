# omnidesk-ai-router — Tools & MCP handout

Everything is in `tools/`. Run scripts from the project root, e.g. `python tools/toolnode_example.py`.

    pip install -r requirements.txt     # then set GROQ_API_KEY in .env

Uses Groq (`langchain-groq`, model `openai/gpt-oss-20b` by default) as the LLM
instead of OpenAI. Get a free API key at https://console.groq.com/keys.

Handout code (verbatim, LLM swapped to Groq): tools_basics, tools_pydantic, tools_structured,
toolnode_example, injected_state_example, error_strategies, mcp_connect_one, mcp_connect_multi,
my_mcp_server (port 8001), use_my_server.

Exercises: exercise_errors, exercise_mcp_connect.
End-of-day test: test_task_tools, test_task_server (port 8002), test_task_client.

For MCP: start the server in one terminal, run its client in another.
