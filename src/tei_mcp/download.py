"""ODD file download logic with env var override and URL fallback."""

import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger("tei-mcp")

# Primary: stable release URL; Fallback: Stylesheets repo copy
DOWNLOAD_URLS = [
    "https://www.tei-c.org/Vault/P5/current/xml/tei/odd/p5subset.xml",
    "https://raw.githubusercontent.com/TEIC/Stylesheets/dev/source/p5subset.xml",
]

DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "p5subset.xml"


def get_odd_path() -> Path:
    """Return the path to the ODD file.

    Uses TEI_ODD_PATH env var if set (validates existence).
    Otherwise returns the default data path.
    """
    env_path = os.environ.get("TEI_ODD_PATH")
    if env_path:
        p = Path(env_path)
        if not p.exists():
            raise FileNotFoundError(
                f"TEI_ODD_PATH points to non-existent file: {env_path}"
            )
        return p
    return DEFAULT_DATA_PATH


async def ensure_odd_file() -> Path:
    """Ensure the ODD file exists, downloading if necessary.

    Returns the path to the ODD file. Downloads from DOWNLOAD_URLS
    with fallback if the file does not already exist.

    Raises:
        RuntimeError: If all download sources fail.
    """
    path = get_odd_path()
    if path.exists():
        logger.info("Using existing ODD file: %s", path)
        return path

    logger.info("Downloading p5subset.xml...")
    path.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        for url in DOWNLOAD_URLS:
            try:
                logger.info("Trying: %s", url)
                resp = await client.get(url)
                resp.raise_for_status()
                path.write_bytes(resp.content)
                logger.info("Downloaded to %s (%d bytes)", path, len(resp.content))
                return path
            except httpx.HTTPError as e:
                logger.warning("Failed to download from %s: %s", url, e)

    raise RuntimeError(
        "Failed to download p5subset.xml from any source. "
        "Check network connectivity or set TEI_ODD_PATH to a local file."
    )
