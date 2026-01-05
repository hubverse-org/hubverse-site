import random
from pathlib import Path
from types import SimpleNamespace
import pytest

from scripts import update_contributors as uc

def make_fake_user(login, *, name=None, blog=None, bio=None, location=None,
                   avatar_url="https://avatar.example/50.png"):
    return SimpleNamespace(
        login=login,
        name=name,
        blog=blog,
        bio=bio,
        location=location,
        avatar_url=avatar_url,
        html_url=f"https://github.com/{login}",
    )

class FakeRepo:
    def __init__(self, name, contributors, error=False):
        self.name = name
        self._contributors = contributors
        self._error = error
    def get_contributors(self):
        if self._error:
            raise Exception("API error")
        return self._contributors

class FakeOrg:
    def __init__(self, repos, users):
        self._repos = repos
        self._users = users
    def get_repos(self):
        return self._repos
    def get_user(self, login):
        return self._users.get(login, make_fake_user(login))

class FakeGithub:
    def __init__(self, org):
        self._org = org
    def get_organization(self, name):
        return self._org

def run_with_tmp_output(tmp_path, repos, users, monkeypatch):
    # Stabilize order for assertions
    monkeypatch.setattr(random, "shuffle", lambda xs: None)
    monkeypatch.setattr(uc, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(uc, "OUTPUT_FILE", str(tmp_path / "contributors.md"))
    g = FakeGithub(FakeOrg(repos, users))
    uc.render_contributors(g)
    return tmp_path / "contributors.md"

def test_end_to_end_writes_contributors(tmp_path, monkeypatch):
    repo_a = FakeRepo("repoA", [make_fake_user("alice"), make_fake_user("dependabot[bot]")])
    repo_b = FakeRepo("repoB", [make_fake_user("bob"), make_fake_user("alice")])
    users = {
        "alice": make_fake_user("alice", name="Alice A.", blog="alice.example", bio="Researcher", location="MA"),
        "bob": make_fake_user("bob"),  # minimal, so plain name
    }
    out_path = run_with_tmp_output(tmp_path, [repo_a, repo_b], users, monkeypatch)
    text = out_path.read_text(encoding="utf-8")

    assert "This page should not be edited directly" in text
    assert "# Contributors to hubverse repositories" in text
    assert "dependabot" not in text

    # Alice: blog normalization + name becomes a link only when blog exists
    assert "- [Alice A.](https://alice.example) ([alice](https://github.com/alice))." in text
    # Bob: no blog → plain name + GitHub link
    assert "- bob ([bob](https://github.com/bob))." in text

    # Bio/location sentences
    assert " Researcher." in text
    assert " MA." in text

    # Aggregated repos sorted
    assert "Repositories contributed to: repoA, repoB." in text

    # One separator between two entries, none at end
    assert text.count("---") == 1
    assert text.strip().endswith(".")  # not ending with '---'

def test_repo_error_is_skipped(tmp_path, monkeypatch):
    repo_err = FakeRepo("repoErr", [], error=True)
    repo_ok = FakeRepo("repoOk", [make_fake_user("carol")])
    users = {"carol": make_fake_user("carol", blog="https://carol.dev", name="Carol")}
    out_path = run_with_tmp_output(tmp_path, [repo_err, repo_ok], users, monkeypatch)
    text = out_path.read_text(encoding="utf-8")
    # With blog present, name appears in brackets
    assert "- [Carol](https://carol.dev) ([carol](https://github.com/carol))." in text
    assert "repoOk" in text
    assert "repoErr" not in text

def test_fallback_on_user_fetch_failure(tmp_path, monkeypatch):
    # No override for 'dave' → minimal user returns; still renders without exception
    repo = FakeRepo("repoX", [make_fake_user("dave")])
    users = {}
    out_path = run_with_tmp_output(tmp_path, [repo], users, monkeypatch)
    text = out_path.read_text(encoding="utf-8")
    assert "- dave ([dave](https://github.com/dave))." in text

def test_blog_scheme_added_only_when_missing(tmp_path, monkeypatch):
    repo = FakeRepo("repoSchemes", [make_fake_user("eve"), make_fake_user("frank")])
    users = {
        "eve": make_fake_user("eve", name="Eve", blog="eve.dev"),             # no scheme → https:// added
        "frank": make_fake_user("frank", name="Frank", blog="http://frank.dev"),  # preserve scheme
    }
    out_path = run_with_tmp_output(tmp_path, [repo], users, monkeypatch)
    text = out_path.read_text(encoding="utf-8")
    assert "(https://eve.dev)" in text
    assert "(http://frank.dev)" in text

