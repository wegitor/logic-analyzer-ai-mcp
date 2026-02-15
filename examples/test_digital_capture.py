import asyncio
import sys
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add src to path
sys.path.insert(0, os.path.abspath('src'))

async def run():
    # Define server parameters
    python_exe = sys.executable
    server_script = os.path.abspath("src/logic_analyzer_mcp.py")
    
    server_params = StdioServerParameters(
        command=python_exe,
        args=[server_script, "--logic2"], 
        env=os.environ.copy()
    )

    print(f"Starting local MCP server instance at: {server_script}...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("--- Connected ---")

            # 1. Connect to Logic 2
            print("Connecting to Logic 2...")
            res = await session.call_tool("logic2_reconnect", {"port": 10430})
            print(f"Result: {res.content[0].text}")

            # 2. Test One-Shot Digital Capture
            print("\nTesting 'capture_and_analyze_digital' (should default to None threshold)...")
            try:
                # We do NOT pass digital_threshold_volts, so it uses the default (None)
                val = await session.call_tool("capture_and_analyze_digital", {
                    "digital_channels": [0, 1],
                    "duration_seconds": 0.5,
                    "sample_rate": 10000000,
                    "output_directory": os.path.abspath("test_output_digital")
                })
                
                # Parse result
                result_text = val.content[0].text
                print("\nSuccess! Analysis Result:")
                # It's a string that looks like python dict representation or json
                # The tool returns a dictionary, so FastMCP serializes it to text (JSON usually)
                try:
                    import ast
                    # fastmcp might return stringified dict or json
                    # Let's try to parse as JSON first
                    parsed = json.loads(result_text)
                    print(json.dumps(parsed, indent=2))
                except:
                    print(result_text)
                    
            except Exception as e:
                print(f"\nError during capture tool call: {e}")

if __name__ == "__main__":
    asyncio.run(run())
