import requests
import types
import io
import os
from pathlib import Path

import pytest

from scripts import update_cite

class DummyResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

def test_fetch_markdown_success(monkeypatch):
    def fake_get(url, timeout=30):
        return DummyResponse("CONTENT")
    monkeypatch.setattr(update_cite.requests, "get", fake_get)
    out = update_cite.fetch_markdown("http://example")
    assert out == "CONTENT"

def test_fetch_markdown_failure_raises(monkeypatch):
    def fake_get(url, timeout=30):
        return DummyResponse("ERR", status_code=500)
    monkeypatch.setattr(update_cite.requests, "get", fake_get)
    with pytest.raises(RuntimeError):
        update_cite.fetch_markdown("http://example")

def test_main_writes_dest_file(tmp_path, monkeypatch, sample_md_with_header):
    # Redirect DEST_FILE to tmp path
    dest = tmp_path / "cite.qmd"
    monkeypatch.setattr(update_cite, "DEST_FILE", str(dest))

    # Stub network to return our sample content
    def fake_get(url, timeout=30):
        return DummyResponse(sample_md_with_header, status_code=200)
    monkeypatch.setattr(update_cite.requests, "get", fake_get)

    # Also override CITE_URL to a dummy
    monkeypatch.setattr(update_cite, "CITE_URL", "http://dummy")

    # Run
    update_cite.main()

    # Assert file created
    assert dest.exists()
    text = dest.read_text(encoding="utf-8")
    # Header present, body transformed
    assert text.startswith("---")
    assert "::: {.callout-note}" in text
    assert "```bibtex" in text
    # The exact H1 "How to cite" should not appear in body (only in YAML title)
    assert "\n# How to cite" not in text

@pytest.mark.parametrize("bad_text", ["", "BibTeX:\n```\n@x{}\n```\n"])
def test_main_handles_minimal_inputs(tmp_path, monkeypatch, bad_text):
    dest = tmp_path / "cite.qmd"
    monkeypatch.setattr(update_cite, "DEST_FILE", str(dest))

    def fake_get(url, timeout=30):
        return DummyResponse(bad_text, status_code=200)
    monkeypatch.setattr(update_cite.requests, "get", fake_get)
    monkeypatch.setattr(update_cite, "CITE_URL", "http://dummy")

    update_cite.main()
    assert dest.exists()
    text = dest.read_text(encoding="utf-8")
    assert text.startswith("---")
    # Always ends with newline due to cleanup_blank_lines
    assert text.endswith("\n")

