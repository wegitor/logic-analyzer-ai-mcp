import logging
import os
import sys

# Add necessary paths for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)  # Add script directory to path

from mcp.server.fastmcp import FastMCP
from controllers.logic2_automation_controller import Logic2AutomationController
from mcp import StdioServerParameters

# Import controllers
from controllers.saleae_parser_controller import SaleaeParserController
from mcp_tools import setup_mcp_tools

def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    print("Starting MCP server for Logic 2...")
    
    try:
        # Create MCP server
        mcp = FastMCP("Logic 2 Control")
        
        # Initialize Logic 2 automation controller
        controller = Logic2AutomationController(manager=None)  # Manager will be initialized in the controller
        
        # Setup MCP tools
        setup_mcp_tools(mcp, controller)
        
        # Setup parser controller
        print("Initializing SaleaeParserController...")
        parser_controller = SaleaeParserController(mcp)
        print("SaleaeParserController initialized successfully.")
        
        # Run MCP server
        logger.info("Starting MCP server...")
        mcp.run()
        
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        raise

if __name__ == "__main__":
    main()