import os
import requests
import random
from collections import defaultdict

# Fetch the token from the environment variable
token = os.getenv("GITHUB_TOKEN")
if not token:
    raise ValueError("GITHUB_TOKEN is not set. Please ensure the environment variable is configured.")

# GitHub API base URL
base_url = "https://api.github.com"
org = "hubverse-org"
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {token}",
}

def get_paginated(url, params=None):
    """Yield items from all pages without recreating the params dict each loop."""
    if params is None:
        params = {}
    # Set per_page once; do not rebuild params each iteration
    params.setdefault("per_page", 100)
    page = 1
    while True:
        params["page"] = page
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            raise ValueError(f"Request failed: {resp.status_code} - {resp.text}")
        items = resp.json()
        if not items:
            break
        for item in items:
            yield item
        page += 1

# Fetch all repositories in the organization (paginate!)
repos_url = f"{base_url}/orgs/{org}/repos"
repos = []
for repo in get_paginated(repos_url, params={"type": "all"}):
    # Skip forks or archived if you want; for now include all shown in UI
    repos.append(repo["name"])

# Dictionary to store contributors and their repositories
contributors = defaultdict(set)

# Fetch contributors for each repository (paginate!)
for repo in repos:
    contrib_url = f"{base_url}/repos/{org}/{repo}/contributors"
    try:
        for contributor in get_paginated(contrib_url):
            login = contributor.get("login")
            if not login:
                continue
            contributors[login].add(repo)
    except ValueError:
        # If contributors endpoint fails for a specific repo, continue
        continue

# Shuffle contributors randomly
contributor_list = list(contributors.items())
random.shuffle(contributor_list)

# Fetch user details and generate output
output_dir = "community"
os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists
output_file = f"{output_dir}/contributors.md"

with open(output_file, "w", encoding="utf-8") as file:
    file.write(
        "<!--\n"
        "This page should not be edited directly as it is automatically regenerated with `scripts/update-contributors.py`\n"
        "-->\n\n"
    )
    file.write("# Contributors to hubverse repositories\n\nThese are the contributors to hubverse repositories in random order.\n\n")

    last_index = len(contributor_list) - 1  # Get last index to avoid trailing '---'

    for i, (login, repo_set) in enumerate(contributor_list):
        if login.startswith("dependabot"):
            continue  # skip bots

        user_resp = requests.get(f"{base_url}/users/{login}", headers=headers)
        if user_resp.status_code != 200:
            file.write(
                f"- ![Avatar](https://dummyimage.com/50x50/3c88be/3c88be) "
                f"- [{login}](https://github.com/{login}) - "
                f"Failed to fetch additional details. (Error {user_resp.status_code})\n"
            )
            continue  # Skip if user data fetch fails

        user_data = user_resp.json()
        name = (user_data.get("name", login) or "").strip()
        github_name = (user_data.get("login") or "").strip()
        blog = (user_data.get("blog") or "").strip()
        bio = " ".join((user_data.get("bio") or "").split())
        location = (user_data.get("location", "") or "").strip()
        avatar_url = user_data.get("avatar_url", "")
        profile_url = user_data.get("html_url", "")

        # Only include square brackets around name if `blog` is not empty
        name_output = f"[{name}]" if name and blog else name
        # Only include the blog link if it's not empty
        if blog and not blog.startswith(("http://", "https://")):
            # If blog doesn't start with http:// or https://, prepend https://
            blog = f"https://{blog}"
        blog_output = f"({blog})" if blog else "" # Don't include parentheses if `blog` is empty
        # Avoid adding period if `bio` or `location` is empty
        bio_output = f" {bio}." if bio else ""
        location_output = f" {location}." if location else ""
        repo_text = ", ".join(sorted(repo_set))

        file.write(
            f'<img src="{avatar_url}" alt="" class="avatar"> '
            f"- {name_output}{blog_output} ([{github_name}]({profile_url}))."
            f"{bio_output}{location_output}\n\n"
            f"Repositories contributed to: {repo_text}.\n\n"
        )
        # Add '---' separator only if it's NOT the last contributor
        if i != last_index:
            file.write("---\n\n")

print("Contributors list updated successfully.")
