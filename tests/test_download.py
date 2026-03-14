"""Tests for download logic with env var override and URL fallback."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tei_mcp.download import DOWNLOAD_URLS, get_odd_path, ensure_odd_file


class TestGetOddPath:
    def test_returns_env_var_path_when_set(self, tmp_path, monkeypatch):
        """get_odd_path() returns Path from TEI_ODD_PATH env var when set."""
        odd_file = tmp_path / "custom.xml"
        odd_file.write_text("<schemaSpec/>")
        monkeypatch.setenv("TEI_ODD_PATH", str(odd_file))
        result = get_odd_path()
        assert result == odd_file

    def test_raises_when_env_var_points_to_nonexistent(self, monkeypatch):
        """get_odd_path() raises FileNotFoundError when TEI_ODD_PATH points to non-existent file."""
        monkeypatch.setenv("TEI_ODD_PATH", "/nonexistent/path/odd.xml")
        with pytest.raises(FileNotFoundError, match="TEI_ODD_PATH"):
            get_odd_path()

    def test_returns_default_path_when_env_var_unset(self, monkeypatch):
        """get_odd_path() returns default data path when TEI_ODD_PATH is not set."""
        monkeypatch.delenv("TEI_ODD_PATH", raising=False)
        result = get_odd_path()
        assert result.name == "p5subset.xml"
        assert "data" in result.parts


class TestEnsureOddFile:
    @pytest.mark.asyncio
    async def test_returns_existing_path_without_download(self, tmp_path, monkeypatch):
        """ensure_odd_file() returns existing path without downloading when file exists."""
        odd_file = tmp_path / "p5subset.xml"
        odd_file.write_text("<schemaSpec/>")
        monkeypatch.setenv("TEI_ODD_PATH", str(odd_file))
        result = await ensure_odd_file()
        assert result == odd_file

    @pytest.mark.asyncio
    async def test_downloads_from_primary_url(self, tmp_path, monkeypatch, odd_xml_bytes):
        """ensure_odd_file() downloads from primary URL on success."""
        odd_file = tmp_path / "data" / "p5subset.xml"
        monkeypatch.delenv("TEI_ODD_PATH", raising=False)

        mock_response = MagicMock()
        mock_response.content = odd_xml_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("tei_mcp.download.DEFAULT_DATA_PATH", odd_file), \
             patch("tei_mcp.download.httpx.AsyncClient", return_value=mock_client):
            result = await ensure_odd_file()

        assert result == odd_file
        assert odd_file.exists()
        mock_client.get.assert_called_once_with(DOWNLOAD_URLS[0])

    @pytest.mark.asyncio
    async def test_falls_back_to_secondary_url(self, tmp_path, monkeypatch, odd_xml_bytes):
        """ensure_odd_file() falls back to secondary URL when primary fails."""
        odd_file = tmp_path / "data" / "p5subset.xml"
        monkeypatch.delenv("TEI_ODD_PATH", raising=False)

        mock_response_ok = MagicMock()
        mock_response_ok.content = odd_xml_bytes
        mock_response_ok.raise_for_status = MagicMock()

        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_response_fail, mock_response_ok])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("tei_mcp.download.DEFAULT_DATA_PATH", odd_file), \
             patch("tei_mcp.download.httpx.AsyncClient", return_value=mock_client):
            result = await ensure_odd_file()

        assert result == odd_file
        assert odd_file.exists()
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_runtime_error_when_all_fail(self, tmp_path, monkeypatch):
        """ensure_odd_file() raises RuntimeError with clear message when all URLs fail."""
        odd_file = tmp_path / "data" / "p5subset.xml"
        monkeypatch.delenv("TEI_ODD_PATH", raising=False)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPError("Connection failed")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("tei_mcp.download.DEFAULT_DATA_PATH", odd_file), \
             patch("tei_mcp.download.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Failed to download"):
                await ensure_odd_file()
