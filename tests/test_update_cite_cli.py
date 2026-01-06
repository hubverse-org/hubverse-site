import pytest
import requests
from unittest.mock import Mock, patch

from scripts import update_cite


@patch("scripts.update_cite.requests.get")
def test_fetch_markdown_success(mock_get):
    mock_get.return_value = Mock(
        text="CONTENT",
        raise_for_status=Mock(),
    )

    out = update_cite.fetch_markdown("http://example")
    assert out == "CONTENT"


@patch("scripts.update_cite.requests.get")
def test_fetch_markdown_failure_raises(mock_get):
    mock_resp = Mock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("HTTP 500")
    mock_get.return_value = mock_resp

    with pytest.raises(RuntimeError):
        update_cite.fetch_markdown("http://example")


@patch("scripts.update_cite.requests.get")
def test_fetch_markdown_failure_raises(mock_get):
    mock_resp = Mock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("HTTP 500")
    mock_get.return_value = mock_resp

    with pytest.raises(RuntimeError):
        update_cite.fetch_markdown("http://example")


@patch("scripts.update_cite.requests.get")
def test_main_writes_dest_file(
    mock_get, tmp_path, monkeypatch, sample_md_with_header
):
    dest = tmp_path / "cite.qmd"
    monkeypatch.setattr(update_cite, "DEST_FILE", str(dest))
    monkeypatch.setattr(update_cite, "CITE_URL", "http://dummy")

    mock_get.return_value = Mock(
        text=sample_md_with_header,
        raise_for_status=Mock(),
    )

    update_cite.main()

    assert dest.exists()
    text = dest.read_text(encoding="utf-8")

    assert text.startswith("---")
    assert "::: {.callout-note}" in text
    assert "```bibtex" in text
    assert "\n# How to cite" not in text


@pytest.mark.parametrize(
    "bad_text",
    ["", "BibTeX:\n```\n@x{}\n```\n"],
)
@patch("scripts.update_cite.requests.get")
def test_main_handles_minimal_inputs(
    mock_get, tmp_path, monkeypatch, bad_text
):
    dest = tmp_path / "cite.qmd"
    monkeypatch.setattr(update_cite, "DEST_FILE", str(dest))
    monkeypatch.setattr(update_cite, "CITE_URL", "http://dummy")

    mock_get.return_value = Mock(
        text=bad_text,
        raise_for_status=Mock(),
    )

    update_cite.main()

    assert dest.exists()
    text = dest.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert text.endswith("\n")

