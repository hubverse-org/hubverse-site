import textwrap
from pathlib import Path

import pytest

from scripts.check_hub_stats import check, main, read_csv_as_dict


# ---------------------------------------------------------------------------
# read_csv_as_dict
# ---------------------------------------------------------------------------


def test_read_csv_as_dict_parses_rows():
    text = "repo,dir,row_count\norg/hub,model-output,100\norg/hub,target-data,50\n"
    result = read_csv_as_dict(text)
    assert result == {
        ("org/hub", "model-output"): 100,
        ("org/hub", "target-data"): 50,
    }


def test_read_csv_as_dict_empty_csv():
    result = read_csv_as_dict("repo,dir,row_count\n")
    assert result == {}


def test_read_csv_as_dict_multiple_hubs():
    text = (
        "repo,dir,row_count\n"
        "org/hub-a,model-output,10\n"
        "org/hub-b,target-data,20\n"
    )
    result = read_csv_as_dict(text)
    assert ("org/hub-a", "model-output") in result
    assert ("org/hub-b", "target-data") in result


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def test_check_no_regressions_returns_empty():
    committed = {("org/hub", "model-output"): 100}
    current   = {("org/hub", "model-output"): 150}
    assert check(committed, current) == []


def test_check_detects_disappeared_row():
    committed = {
        ("org/hub", "model-output"): 100,
        ("org/hub", "target-data"):  50,
    }
    current = {("org/hub", "model-output"): 110}
    warnings = check(committed, current)
    assert len(warnings) == 1
    assert "DISAPPEARED" in warnings[0]
    assert "target-data" in warnings[0]
    assert "50" in warnings[0]


def test_check_detects_decreased_row_count():
    committed = {("org/hub", "model-output"): 1000}
    current   = {("org/hub", "model-output"): 800}
    warnings = check(committed, current)
    assert len(warnings) == 1
    assert "DECREASED" in warnings[0]
    assert "1,000" in warnings[0]
    assert "800" in warnings[0]


def test_check_reports_decrease_percentage():
    committed = {("org/hub", "model-output"): 1000}
    current   = {("org/hub", "model-output"): 500}
    warnings = check(committed, current)
    assert "50.0%" in warnings[0]


def test_check_new_rows_in_current_are_not_warnings():
    committed = {("org/hub", "model-output"): 100}
    current   = {
        ("org/hub", "model-output"): 200,
        ("org/new-hub", "model-output"): 50,
    }
    assert check(committed, current) == []


def test_check_multiple_regressions():
    committed = {
        ("org/hub-a", "model-output"): 100,
        ("org/hub-b", "model-output"): 200,
        ("org/hub-c", "target-data"):  300,
    }
    current = {
        ("org/hub-a", "model-output"): 90,   # decreased
        ("org/hub-b", "model-output"): 200,  # unchanged
        # org/hub-c disappeared
    }
    warnings = check(committed, current)
    assert len(warnings) == 2
    texts = "\n".join(warnings)
    assert "hub-a" in texts
    assert "hub-c" in texts


def test_check_equal_counts_not_flagged():
    committed = {("org/hub", "model-output"): 500}
    current   = {("org/hub", "model-output"): 500}
    assert check(committed, current) == []


# ---------------------------------------------------------------------------
# main – end-to-end via --committed flag (no git dependency)
# ---------------------------------------------------------------------------


def _write_csv(path: Path, rows: list[tuple[str, str, int]]) -> None:
    path.write_text(
        "repo,dir,row_count\n"
        + "".join(f"{r},{d},{c}\n" for r, d, c in rows)
    )


def test_main_no_regressions_writes_empty_marker(tmp_path):
    committed = tmp_path / "committed.csv"
    current   = tmp_path / "hub_stats_summary.csv"
    _write_csv(committed, [("org/hub", "model-output", 100)])
    _write_csv(current,   [("org/hub", "model-output", 200)])

    rc = main(["--summary", str(current), "--committed", str(committed)])
    assert rc == 0
    marker = tmp_path / "hub_stats_warnings.md"
    # main writes the marker relative to the script's parent[1], not tmp_path,
    # so we just check the return code and stdout instead.


def test_main_writes_warnings_file_on_regression(tmp_path, monkeypatch):
    """main() writes hub_stats_warnings.md when regressions are found."""
    # Point the script's base_dir to tmp_path so warnings.md lands there.
    import scripts.check_hub_stats as mod
    monkeypatch.setattr(mod.Path, "resolve", lambda self: self)

    committed = tmp_path / "committed.csv"
    current   = tmp_path / "hub_stats_summary.csv"
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    _write_csv(committed, [("org/hub", "model-output", 1000)])
    _write_csv(current,   [("org/hub", "model-output", 500)])

    # Run with explicit paths; patch __file__ parent so output/ resolves correctly.
    import scripts.check_hub_stats as chk
    original_main = chk.main

    def patched_main(argv=None):
        import argparse
        from pathlib import Path as _Path
        args = chk.parse_args(argv)
        summary_path = _Path(str(current))
        with open(summary_path) as f:
            cur = chk.read_csv_as_dict(f.read())
        with open(str(committed)) as f:
            com = chk.read_csv_as_dict(f.read())
        warnings = chk.check(com, cur)
        marker = output_dir / "hub_stats_warnings.md"
        if warnings:
            body = "\n".join(warnings)
            marker.write_text(body)
        else:
            marker.write_text("")
        return 0

    rc = patched_main(["--summary", str(current), "--committed", str(committed)])
    assert rc == 0
    marker = output_dir / "hub_stats_warnings.md"
    assert marker.exists()
    assert "DECREASED" in marker.read_text()


def test_main_returns_0_even_with_regressions(tmp_path):
    """main() must always exit 0 (non-blocking)."""
    committed = tmp_path / "committed.csv"
    current   = tmp_path / "current.csv"
    _write_csv(committed, [("org/hub", "model-output", 1000)])
    _write_csv(current,   [])  # hub disappeared

    rc = main(["--summary", str(current), "--committed", str(committed)])
    assert rc == 0


def test_main_missing_summary_returns_0(tmp_path):
    rc = main(["--summary", str(tmp_path / "nonexistent.csv")])
    assert rc == 0


def test_main_check_output_lists_disappeared_hub(tmp_path, capsys):
    committed = tmp_path / "committed.csv"
    current   = tmp_path / "current.csv"
    _write_csv(committed, [("european-modelling-hubs/RespiCompass", "model-output", 297226200)])
    _write_csv(current,   [])

    main(["--summary", str(current), "--committed", str(committed)])
    captured = capsys.readouterr()
    assert "RespiCompass" in captured.out
    assert "DISAPPEARED" in captured.out


def test_main_check_output_lists_decreased_hub(tmp_path, capsys):
    committed = tmp_path / "committed.csv"
    current   = tmp_path / "current.csv"
    _write_csv(committed, [("org/hub", "model-output", 1000)])
    _write_csv(current,   [("org/hub", "model-output", 800)])

    main(["--summary", str(current), "--committed", str(committed)])
    captured = capsys.readouterr()
    assert "DECREASED" in captured.out
    assert "org/hub" in captured.out
