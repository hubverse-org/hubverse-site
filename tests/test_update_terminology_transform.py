import re

from scripts.update_terminology import process_definitions, process_abbreviations


def test_remove_top_header(sample_defs_md):
    out = process_definitions(sample_defs_md)
    assert not out.lstrip().startswith("# Terminology")


def test_modeling_tasks_section_rewritten(sample_defs_md):
    out = process_definitions(sample_defs_md)
    assert "## Modeling Tasks Terminology {#model-tasks}" in out
    assert "Learn more about modeling tasks" in out
    assert "docs.hubverse.io" in out


def test_prediction_terminology_figure_rewritten(sample_defs_md):
    out = process_definitions(sample_defs_md)
    assert "{#prediction-terms}" in out
    assert "horizon-nomenclature.png" in out
    assert "fig-alt=" in out


def test_admonition_converted_to_definition_list(sample_defs_md):
    out = process_definitions(sample_defs_md)

    # Term
    assert "[Nowcast]{#def-nowcast}" in out
    assert ": A short-term estimate (#model-output)." in out

    # Second term without anchor
    assert "[Forecast]" in out
    assert ": A future prediction." in out


def test_internal_def_links_fixed(sample_defs_md):
    out = process_definitions(sample_defs_md)
    assert "(#model-output)" in out
    assert "(#def-model-output)" not in out


def test_no_admonition_fences_remain(sample_defs_md):
    out = process_definitions(sample_defs_md)
    assert "```{admonition}" not in out
    assert "```" not in out


def test_blank_lines_compacted(sample_defs_md):
    out = process_definitions(sample_defs_md)
    assert "\n\n\n" not in out


def test_process_abbreviations_noop(sample_abbr_md):
    out = process_abbreviations(sample_abbr_md)
    assert out == sample_abbr_md

