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
