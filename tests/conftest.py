from pathlib import Path

import pytest


@pytest.fixture
def test_odd_path() -> Path:
    """Return path to the small test ODD XML fixture."""
    return Path(__file__).parent / "fixtures" / "test_odd.xml"


@pytest.fixture
def odd_xml_bytes(test_odd_path: Path) -> bytes:
    """Return the test ODD XML as bytes (for mocking download)."""
    return test_odd_path.read_bytes()
