import sys
sys.path.insert(0, 'src')
from mcp.server.fastmcp import FastMCP
from controllers.logic2_automation_controller import Logic2AutomationController
from mcp_tools_experimental import setup_mcp_tools_experimental

mcp = FastMCP('test')
ctrl = Logic2AutomationController(manager=None)
setup_mcp_tools_experimental(mcp, ctrl)
print('OK - all experimental tools registered')
