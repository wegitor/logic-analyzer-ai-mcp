import logging
import os
import sys
import argparse
from typing import Optional

# Add necessary paths for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)  # Add script directory to path

from mcp.server.fastmcp import FastMCP
from controllers.logic2_automation_controller import Logic2AutomationController
from mcp import StdioServerParameters

# Import controllers
from controllers.saleae_parser_controller import SaleaeParserController
from mcp_tools import setup_mcp_tools

def main(enable_logic2: Optional[bool] = None):
    """Start the MCP server. If enable_logic2 is None, CLI args/env determine it."""
    # Setup logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Determine enable_logic2 from args if not explicitly provided
    if enable_logic2 is None:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('--logic2', action='store_true', help='Enable Logic2 experimental MCP tools')
        # parse only known args, leave others untouched
        args, _ = parser.parse_known_args()
        enable_logic2 = bool(args.logic2) or (os.environ.get("LOGIC2") and str(os.environ.get("LOGIC2")).lower() in ("1", "true", "yes"))

    logger.info("Starting MCP server for Logic 2...")

    try:
        # Create MCP server
        mcp = FastMCP("Logic 2 Control")

        # Initialize Logic 2 automation controller
        controller = Logic2AutomationController(manager=None)  # Manager will be initialized in the controller

        # Setup MCP tools (pass enable_logic2)
        setup_mcp_tools(mcp, controller, enable_logic2=enable_logic2)

        # Setup parser controller
        logger.info("Initializing SaleaeParserController...")
        parser_controller = SaleaeParserController(mcp)
        logger.info("SaleaeParserController initialized successfully.")

        # Run MCP server
        logger.info("Starting MCP server...")
        mcp.run()

    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        raise

if __name__ == "__main__":
    main()