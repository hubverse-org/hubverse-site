import os
import random
from collections import defaultdict
from github import Github

# Initialize with token
token = os.getenv("GITHUB_TOKEN")
if not token:
    raise ValueError("GITHUB_TOKEN is not set.")

g = Github(token)
org = g.get_organization("hubverse-org")

# Get all repos - pagination handled automatically!
repos = list(org.get_repos())

# Dictionary to store contributors
contributors = defaultdict(set)

# Fetch contributors for each repository
for repo in repos:
    try:
        for contributor in repo.get_contributors():
            if not contributor.login.startswith("dependabot"):
                contributors[contributor.login].add(repo.name)
    except Exception:
        continue  # Skip repos where contributors fetch fails

# Shuffle and prepare output
contributor_list = list(contributors.items())
random.shuffle(contributor_list)
last_index = len(contributor_list) - 1

# Generate output file
output_dir = "community"
os.makedirs(output_dir, exist_ok=True)
output_file = f"{output_dir}/contributors.md"

with open(output_file, "w", encoding="utf-8") as file:
    file.write(
        "<!--\n"
        "This page should not be edited directly as it is automatically regenerated with `scripts/update-contributors.py`\n"
        "-->\n\n"
    )
    file.write("# Contributors to hubverse repositories\n\nThese are the contributors to hubverse repositories in random order.\n\n")

    for i, (login, repo_set) in enumerate(contributor_list):
        try:
            user = g.get_user(login)
            name = user.name or login
            blog = user.blog or ""
            bio = " ".join((user.bio or "").split())
            location = user.location or ""

            # Format outputs
            name_output = f"[{name}]" if name and blog else name
            if blog and not blog.startswith(("http://", "https://")):
                blog = f"https://{blog}"
            blog_output = f"({blog})" if blog else ""
            bio_output = f" {bio}." if bio else ""
            location_output = f" {location}." if location else ""
            repo_text = ", ".join(sorted(repo_set))

            file.write(
                f'<img src="{user.avatar_url}" alt="" class="avatar"> '
                f"- {name_output}{blog_output} ([{login}]({user.html_url}))."
                f"{bio_output}{location_output}\n\n"
                f"Repositories contributed to: {repo_text}.\n\n"
            )

            if i != last_index:
                file.write("---\n\n")

        except Exception as e:
            file.write(
                f"- ![Avatar](https://dummyimage.com/50x50/3c88be/3c88be) "
                f"- [{login}](https://github.com/{login}) - "
                f"Failed to fetch additional details.\n"
            )
            if i != last_index:
                file.write("---\n\n")

print("Contributors list updated successfully.")
