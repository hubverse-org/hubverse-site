import os
import random
from collections import defaultdict
from types import SimpleNamespace
from github import Github

# Paths used for output; tests can monkeypatch these
OUTPUT_DIR = "community"
OUTPUT_FILE = f"{OUTPUT_DIR}/contributors.md"

def get_user_safe(g, login):
    """
    Fetch a user from GitHub, but never throw.
    Returns a fully shaped minimal user if the API call fails.
    """
    try:
        return g.get_user(login)
    except Exception:
        return SimpleNamespace(
            login=login,
            name=login,
            blog="",
            bio="",
            location="",
            avatar_url="https://dummyimage.com/50x50/3c88be/3c88be",
            html_url=f"https://github.com/{login}",
        )

def render_contributors(g: Github, org_name: str = "hubverse-org") -> None:
    """
    Build the contributors page using the provided Github client.
    All network and data logic happen here; main() just wires a real client.
    """
    org = g.get_organization(org_name)
    repos = list(org.get_repos())

    # Aggregate contributors per repo, skipping automated accounts
    contributors = defaultdict(set)
    for repo in repos:
        try:
            for contributor in repo.get_contributors():
                if not contributor.login.startswith("dependabot"):
                    contributors[contributor.login].add(repo.name)
        except Exception:
            # Skip repos that fail to fetch contributors
            continue

    # Randomize display order; tests may monkeypatch this to be stable
    contributor_list = list(contributors.items())
    random.shuffle(contributor_list)
    last_index = len(contributor_list) - 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write(
            "<!--\n"
            "This page should not be edited directly as it is automatically regenerated with `scripts/update_contributors.py`\n"
            "-->\n\n"
        )
        file.write(
            "# Contributors to hubverse repositories\n\n"
            "These are the contributors to hubverse repositories in random order.\n\n"
        )

        for i, (login, repo_set) in enumerate(contributor_list):
            try:
                # Safe user fetch guards tests against exceptions
                user = get_user_safe(g, login)

                name = user.name or login
                blog = user.blog or ""
                bio = " ".join((user.bio or "").split())
                location = user.location or ""

                # Name becomes a link if a blog exists
                name_output = f"[{name}]" if name and blog else name

                # Normalize blog scheme if present without http(s)
                if blog and not blog.startswith(("http://", "https://")):
                    blog = f"https://{blog}"
                blog_output = f"({blog})" if blog else ""

                # Add sentences for bio and location if they exist
                bio_output = f" {bio}." if bio else ""
                location_output = f" {location}." if location else ""

                # Sorted repo list for determinism
                repo_text = ", ".join(sorted(repo_set))

                file.write(
                    f'<img src="{user.avatar_url}" alt="" class="avatar"> '
                    f"- {name_output}{blog_output} ([{login}]({user.html_url}))."
                    f"{bio_output}{location_output}\n\n"
                    f"Repositories contributed to: {repo_text}.\n\n"
                )

                if i != last_index:
                    file.write("---\n\n")

            except Exception:
                # Fallback when rendering fails unexpectedly
                file.write(
                    f"- ![Avatar](https://dummyimage.com/50x50/3c88be/3c88be) "
                    f"- [{login}](https://github.com/{login}) - "
                    f"Failed to fetch additional details.\n"
                )
                if i != last_index:
                    file.write("---\n\n")

def main() -> None:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN is not set.")
    g = Github(token)
    render_contributors(g)

if __name__ == "__main__":
    main()

