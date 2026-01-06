import os
from unittest.mock import MagicMock
import pytest

from scripts.update_contributors import (
    get_github_client,
    fetch_contributors,
    write_contributors_file,
)

# Test 1: missing token
def test_get_github_client_no_token():
    with pytest.raises(ValueError, match="GITHUB_TOKEN is not set"):
        get_github_client(None)

# Test 2: fetching contributors (including filtering)
def test_fetch_contributors_filters_dependabot():
    # Mock contributors
    alice = MagicMock(login="alice")
    dependabot = MagicMock(login="dependabot[bot]")

    repo1 = MagicMock()
    repo1.name = "repo1"
    repo1.get_contributors.return_value = [alice, dependabot]

    repo2 = MagicMock()
    repo2.name = "repo2"
    repo2.get_contributors.return_value = [alice]

    org = MagicMock()
    org.get_repos.return_value = [repo1, repo2]

    contributors = fetch_contributors(org)

    assert "alice" in contributors
    assert contributors["alice"] == {"repo1", "repo2"}
    assert not any(k.startswith("dependabot") for k in contributors)

# Test 3: repo contributor fetch failure is skipped
def test_fetch_contributors_skips_failing_repo():
    repo_ok = MagicMock()
    repo_ok.name = "ok"
    repo_ok.get_contributors.return_value = [MagicMock(login="bob")]

    repo_fail = MagicMock()
    repo_fail.get_contributors.side_effect = Exception("API error")

    org = MagicMock()
    org.get_repos.return_value = [repo_ok, repo_fail]

    contributors = fetch_contributors(org)

    assert contributors == {"bob": {"ok"}}

# Test 4: write file successfully
def test_write_contributors_file(tmp_path):
    github = MagicMock()

    user = MagicMock()
    user.name = "Alice Smith"
    user.blog = "example.com"
    user.bio = "  Open source contributor "
    user.location = "USA"
    user.avatar_url = "https://avatar"
    user.html_url = "https://github.com/alice"

    github.get_user.return_value = user

    contributors = {"alice": {"repo1", "repo2"}}

    output_file = write_contributors_file(
        github,
        contributors,
        output_dir=tmp_path,
        shuffle=False,
    )

    content = (tmp_path / "contributors.md").read_text()

    assert "Alice Smith" in content
    assert "https://example.com" in content
    assert "Open source contributor." in content
    assert "USA." in content
    assert "repo1, repo2" in content

# Test 5: fallback when user lookup fails
def test_write_contributors_file_user_failure(tmp_path):
    github = MagicMock()
    github.get_user.side_effect = Exception("User not found")

    contributors = {"ghost": {"repo1"}}

    write_contributors_file(
        github,
        contributors,
        output_dir=tmp_path,
        shuffle=False,
    )

    content = (tmp_path / "contributors.md").read_text()

    assert "Failed to fetch additional details" in content
    assert "ghost" in content

