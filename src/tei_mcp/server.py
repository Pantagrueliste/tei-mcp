"""FastMCP server for querying the TEI P5 ODD specification."""

# Configure logging to stderr BEFORE any other imports that might set up logging.
import logging
import sys

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tei-mcp")

from fastmcp import FastMCP  # noqa: E402
from fastmcp.server.lifespan import lifespan  # noqa: E402

from tei_mcp.download import ensure_odd_file  # noqa: E402
from tei_mcp.parser import parse_odd  # noqa: E402


@lifespan
async def app_lifespan(server):
    """Download (if needed) and parse p5subset.xml at server startup."""
    odd_path = await ensure_odd_file()
    logger.info("Parsing ODD file: %s", odd_path)
    store = parse_odd(odd_path)
    logger.info(
        "Loaded %d elements, %d classes, %d macros, %d modules",
        store.element_count,
        store.class_count,
        store.macro_count,
        store.module_count,
    )
    try:
        yield {"store": store}
    finally:
        logger.info("Server shutting down")


mcp = FastMCP("tei-mcp", lifespan=app_lifespan)

# Tools will be added in Phase 2+


def main():
    """Entry point for the tei-mcp console script."""
    mcp.run()
