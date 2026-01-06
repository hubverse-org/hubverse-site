import re

from scripts.update_cite import (
    remove_top_header,
    convert_admonitions_to_callouts,
    normalize_bibtex_fences,
    cleanup_blank_lines,
    build_header,
    process_cite_markdown,
)


def test_remove_top_header_strips_h1(sample_md_with_header):
    md = remove_top_header(sample_md_with_header)
    assert not md.lstrip().startswith("# How to cite")
    assert "Some intro text." in md


def test_remove_top_header_noop_when_absent(sample_md_without_header):
    md = remove_top_header(sample_md_without_header)
    assert md.startswith("Some intro text without H1.")


def test_convert_admonitions_to_callouts_blocks(sample_md_with_header):
    md = remove_top_header(sample_md_with_header)
    out = convert_admonitions_to_callouts(md)

    assert "::: {.callout-note}" in out
    assert "## Note" in out
    assert "Use Vancouver style for journal articles." in out
    assert "```{admonition}" not in out
    assert out.count(":::") >= 2


def test_convert_multiple_admonitions():
    src = (
        "```{admonition} First\nBody A\n```\n\n"
        "```{admonition} Second\nBody B\n```"
    )
    out = convert_admonitions_to_callouts(src)

    assert out.count("::: {.callout-note}") == 2
    assert "## First" in out and "Body A" in out
    assert "## Second" in out and "Body B" in out


def test_normalize_bibtex_fences_after_label(sample_md_with_header):
    md = remove_top_header(sample_md_with_header)
    md = convert_admonitions_to_callouts(md)
    out = normalize_bibtex_fences(md)

    lines = out.splitlines()
    found = False

    for i, line in enumerate(lines):
        if re.match(r"^\s*BibTeX:\s*$", line):
            assert lines[i + 1].strip() == "```bibtex"
            found = True
            break

    assert found, "Did not find 'BibTeX:' label in output"
    assert "```python" in out


def test_normalize_bibtex_fences_preserves_already_fenced(
    sample_bibtex_already_fenced,
):
    out = normalize_bibtex_fences(sample_bibtex_already_fenced)
    assert out.strip().startswith("```bibtex")
    assert "@article{key2024" in out


def test_cleanup_blank_lines_compresses(sample_md_mixed_blanklines):
    out = cleanup_blank_lines(sample_md_mixed_blanklines)
    assert "\n\n\n" not in out
    assert out.endswith("\n")


def test_build_header_has_yaml_and_comment():
    header = build_header()
    assert header.startswith("---")
    assert 'title: "How to cite"' in header
    assert header.strip().endswith("-->")


def test_process_cite_markdown_end_to_end(sample_md_with_header):
    body = process_cite_markdown(sample_md_with_header)

    assert not body.lstrip().startswith("# How to cite")
    assert "::: {.callout-note}" in body
    assert "## Note" in body
    assert "```bibtex" in body
    assert "```python" in body
    assert "\n\n\n" not in body

