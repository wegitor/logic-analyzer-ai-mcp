import asyncio
import sys
import os
import json
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import ClientSession

# Add src to python path for local imports if needed by server subprocess
sys.path.insert(0, os.path.abspath('src'))

async def run():
    print("--- starting MCP Client Demo ---")
    
    # 1. Start Server Process
    server_script = os.path.abspath("src/logic_analyzer_mcp.py")
    python_exe = sys.executable 
    
    server_params = StdioServerParameters(
        command=python_exe,
        args=[server_script, "--logic2"], 
        env=os.environ.copy()
    )

    print(f"Connecting to server: {server_script}")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("--- Connected & Initialized ---")

            # 2. Connect Logic 2
            print("\n[Action] Reconnecting to Logic 2...")
            res = await session.call_tool("logic2_reconnect", {"port": 10430})
            print(f"Result: {res.content[0].text}")

            # 3. Capture & Analyze
            print("\n[Action] Capture & Analyze (Digital)...")
            # We omit 'digital_threshold_volts' so it uses the new default=None
            try:
                result = await session.call_tool("capture_and_analyze_digital", {
                    "digital_channels": [0, 1],
                    "duration_seconds": 0.5,
                    "sample_rate": 10000000
                })
                
                # Parse & Pretty Print
                content = result.content[0].text
                try:
                    data = json.loads(content)
                    print("\n--- Analysis Result ---")
                    print(json.dumps(data, indent=2))
                except:
                    print("\n--- Project Result (Raw) ---")
                    print(content)
                    
            except Exception as e:
                print(f"Error calling tool: {e}")

if __name__ == "__main__":
    asyncio.run(run())
