import yaml

from scripts.print_org_list import build_org_list
from scripts.print_org_list import write_orgs_qmd


SAMPLE = """---
hubs:
  example:
    name: "Example Organization"
    logo: /includes/img/example-logo.png
    hubs: []
  hubverse:
    name: "The hubverse"
    logo: /brand/logo/logo-with-text.png
    hubs: []
  reichlab-modeldev:
    name: "Reich Lab"
    logo: /includes/img/reichlab.png
    hubs: []
  reichlab-training:
    name: "Reich Lab"
    logo: /includes/img/reichlab.png
    hubs: []
  ecdc:
    name: "European Centre for Disease Prevention and Control (ECDC)"
    logo: /includes/img/ecdc.png
    hubs: []
  ecdc-archival:
    name: "European Centre for Disease Prevention and Control (ECDC)"
    logo: /includes/img/ecdc.png
    hubs: []
---
"""


def _write(tmp_path, text=SAMPLE):
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(text, encoding="utf-8")
    return qmd


def test_skips_example_org(tmp_path):
    orgs = build_org_list(_write(tmp_path))
    assert all(o["id"] != "example" for o in orgs)


def test_dedupes_by_name_keeping_first_slug(tmp_path):
    orgs = build_org_list(_write(tmp_path))
    ids = [o["id"] for o in orgs]
    names = [o["name"] for o in orgs]

    # Each organization name appears exactly once
    assert len(names) == len(set(names))
    # First slug wins for each duplicated organization
    assert "reichlab-modeldev" in ids and "reichlab-training" not in ids
    assert "ecdc" in ids and "ecdc-archival" not in ids


def test_preserves_file_order(tmp_path):
    orgs = build_org_list(_write(tmp_path))
    assert [o["id"] for o in orgs] == ["hubverse", "reichlab-modeldev", "ecdc"]


def test_carries_name_and_logo(tmp_path):
    orgs = build_org_list(_write(tmp_path))
    reichlab = next(o for o in orgs if o["id"] == "reichlab-modeldev")
    assert reichlab["name"] == "Reich Lab"
    assert reichlab["logo"] == "/includes/img/reichlab.png"


def test_write_orgs_qmd_roundtrips(tmp_path):
    orgs = build_org_list(_write(tmp_path))
    out = tmp_path / "orgs.qmd"
    write_orgs_qmd(orgs, out)

    parsed = list(yaml.safe_load_all(out.read_text()))[0]
    assert parsed["orgs"] == orgs
