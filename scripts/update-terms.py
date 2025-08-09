import requests

SRC_URL = "https://raw.githubusercontent.com/hubverse-org/hubDocs/main/docs/source/overview/abbreviations.md"
DEST_FILE = "terms.qmd"

def main():
    # Download the markdown file
    resp = requests.get(SRC_URL)
    resp.raise_for_status()
    md = resp.text

    # Replace the issue link
    md = md.replace(
        "[filing an issue on the hubDocs GitHub repository](https://github.com/hubverse-org/hubDocs/issues)",
        "[filing an issue on the hubverse site GitHub repository](https://github.com/hubverse-org/hubverse-site/issues)"
    )

    # Add Quarto YAML header
    header = "---\ntitle: \"Terms\"\n---\n"
    md = f"{header}\n{md}"

    # Save to file
    with open(DEST_FILE, "w", encoding="utf-8") as f:
        f.write(md)

if __name__ == "__main__":
    main()

