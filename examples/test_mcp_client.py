import asyncio
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add src to path to ensure we can find the module if needed, 
# though we will run it as a subprocess
sys.path.insert(0, os.path.abspath('src'))

async def run():
    # Define server parameters
    # We use the python executable from the virtual environment
    python_exe = sys.executable
    server_script = os.path.abspath("src/logic_analyzer_mcp.py")
    
    server_params = StdioServerParameters(
        command=python_exe,
        args=[server_script, "--logic2"], # Enable Logic2 tools
        env=os.environ.copy()
    )

    print(f"Connecting to MCP server at: {server_script}...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            print("\n--- Connected & Initialized ---")

            # List Tools
            print("\n--- Listing Tools ---")
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description[:60]}...")

            # Call a Tool: get_available_devices
            print("\n--- Calling Tool: get_available_devices ---")
            try:
                result = await session.call_tool("get_available_devices", {})
                print(f"Result: {result.content}")
            except Exception as e:
                print(f"Error calling tool: {e}")

            # Call a Tool: logic2_reconnect (to ensure connection)
            print("\n--- Calling Tool: logic2_reconnect ---")
            try:
                result = await session.call_tool("logic2_reconnect", {"port": 10430})
                print(f"Result: {result.content}")
            except Exception as e:
                print(f"Error calling tool: {e}")

if __name__ == "__main__":
    asyncio.run(run())
