import requests
import pytest
from pathlib import Path

from scripts import update_terminology


class DummyResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_fetch_markdown_success(monkeypatch):
    def fake_get(url):
        return DummyResponse("CONTENT")

    monkeypatch.setattr(update_terminology.requests, "get", fake_get)
    assert update_terminology.fetch_markdown("http://x") == "CONTENT"


def test_fetch_markdown_failure(monkeypatch):
    def fake_get(url):
        return DummyResponse("ERR", status_code=500)

    monkeypatch.setattr(update_terminology.requests, "get", fake_get)

    with pytest.raises(RuntimeError):
        update_terminology.fetch_markdown("http://x")


def test_main_writes_file(tmp_path, monkeypatch, sample_defs_md, sample_abbr_md):
    dest = tmp_path / "terminology.qmd"
    monkeypatch.setattr(update_terminology, "DEST_FILE", str(dest))

    def fake_get(url):
        if "terminology.md" in url:
            return DummyResponse(sample_defs_md)
        return DummyResponse(sample_abbr_md)

    monkeypatch.setattr(update_terminology.requests, "get", fake_get)

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


@pytest.mark.parametrize("defs,abbr", [("", ""), ("#", "")])
def test_main_handles_minimal_inputs(tmp_path, monkeypatch, defs, abbr):
    dest = tmp_path / "terminology.qmd"
    monkeypatch.setattr(update_terminology, "DEST_FILE", str(dest))

    def fake_get(url):
        return DummyResponse(defs if "terminology" in url else abbr)

    monkeypatch.setattr(update_terminology.requests, "get", fake_get)

    update_terminology.main()
    assert dest.exists()

