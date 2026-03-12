import pytest
import requests
from unittest.mock import Mock, patch

from scripts import update_terminology


@patch("scripts.update_terminology.requests.get")
def test_fetch_markdown_success(mock_get):
    mock_get.return_value = Mock(
        text="CONTENT",
        raise_for_status=Mock(),
    )

    assert update_terminology.fetch_markdown("http://x") == "CONTENT"


@patch("scripts.update_terminology.requests.get")
def test_fetch_markdown_failure(mock_get):
    mock_resp = Mock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("HTTP 500")
    mock_get.return_value = mock_resp

    with pytest.raises(RuntimeError):
        update_terminology.fetch_markdown("http://x")


@patch("scripts.update_terminology.requests.get")
def test_main_writes_file(
    mock_get, tmp_path, monkeypatch, sample_defs_md, sample_abbr_md
):
    dest = tmp_path / "terminology.qmd"
    monkeypatch.setattr(update_terminology, "DEST_FILE", str(dest))

    def side_effect(url, timeout=30):
        if "terminology.md" in url:
            return Mock(text=sample_defs_md, raise_for_status=Mock())
        return Mock(text=sample_abbr_md, raise_for_status=Mock())

    mock_get.side_effect = side_effect

    update_terminology.main()

    assert dest.exists()
    text = dest.read_text(encoding="utf-8")

    # YAML header
    assert text.startswith("---")
    assert 'title: "Terminology"' in text

    # Definitions transformed
    assert "[Nowcast]{#def-nowcast}" in text

    # Abbreviations included
    assert "Centers for Disease Control" in text


@patch("scripts.update_terminology.requests.get")
def test_main_writes_nav_block(
    mock_get, tmp_path, monkeypatch, sample_defs_md, sample_abbr_md
):
    dest = tmp_path / "terminology.qmd"
    monkeypatch.setattr(update_terminology, "DEST_FILE", str(dest))

    def side_effect(url, timeout=30):
        if "terminology.md" in url:
            return Mock(text=sample_defs_md, raise_for_status=Mock())
        return Mock(text=sample_abbr_md, raise_for_status=Mock())

    mock_get.side_effect = side_effect

    update_terminology.main()

    text = dest.read_text(encoding="utf-8")
    assert ":::: {.page-nav}" in text
    assert "/about.qmd" in text    # prev link
    assert "/funding.md" in text   # next link
    assert text.rstrip().endswith("::::")  # nav block is last


@pytest.mark.parametrize("defs,abbr", [("", ""), ("#", "")])
@patch("scripts.update_terminology.requests.get")
def test_main_handles_minimal_inputs(
    mock_get, tmp_path, monkeypatch, defs, abbr
):
    dest = tmp_path / "terminology.qmd"
    monkeypatch.setattr(update_terminology, "DEST_FILE", str(dest))

    def side_effect(url, timeout=30):
        return Mock(
            text=defs if "terminology" in url else abbr,
            raise_for_status=Mock(),
        )

    mock_get.side_effect = side_effect

    update_terminology.main()
    assert dest.exists()

