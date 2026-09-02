#!/usr/bin/env bash
set -euo pipefail

# All tools installed under $HOME/bin — no root required
mkdir -p "$HOME/bin"
export PATH="$HOME/bin:$PATH"

# --------------------------------------------------------------------------- #
# Install Quarto (tar.gz, no dpkg/root needed)
# --------------------------------------------------------------------------- #
QUARTO_VERSION="${QUARTO_VERSION:-1.6.40}"
QUARTO_TGZ="quarto-${QUARTO_VERSION}-linux-amd64.tar.gz"

echo "Installing Quarto ${QUARTO_VERSION}..."
wget -q "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/${QUARTO_TGZ}"
mkdir -p "$HOME/quarto"
tar -xzf "${QUARTO_TGZ}" -C "$HOME/quarto" --strip-components=1
export PATH="$HOME/quarto/bin:$PATH"
rm "${QUARTO_TGZ}"

# --------------------------------------------------------------------------- #
# Install yq
# --------------------------------------------------------------------------- #
YQ_VERSION="v4.45.1"
echo "Installing yq ${YQ_VERSION}..."
wget -q "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64" \
    -O "$HOME/bin/yq"
chmod +x "$HOME/bin/yq"

# --------------------------------------------------------------------------- #
# Install gh CLI
# --------------------------------------------------------------------------- #
echo "Installing gh CLI..."
wget -q https://github.com/cli/cli/releases/download/v2.67.0/gh_2.67.0_linux_amd64.tar.gz
tar xzf gh_2.67.0_linux_amd64.tar.gz
mv gh_2.67.0_linux_amd64/bin/gh "$HOME/bin/gh"
rm -rf gh_2.67.0_linux_amd64 gh_2.67.0_linux_amd64.tar.gz

# --------------------------------------------------------------------------- #
# Install Python dependencies
# --------------------------------------------------------------------------- #
echo "Installing Python dependencies..."
pip install -r requirements/requirements.txt

# --------------------------------------------------------------------------- #
# Generate content (requires GITHUB_TOKEN in Netlify environment variables)
# --------------------------------------------------------------------------- #
echo "Generating content..."
# Note: `make models` is intentionally omitted. Model counts in
# _data/active-hubs.qmd are updated and committed by the Update Hub Stats
# workflow, so running it here would trigger redundant GitHub API calls and
# risk rate-limiting (see .github/workflows/publish.yml).
make contributors
make orgs
make terminology
make cite

# --------------------------------------------------------------------------- #
# Render site
# --------------------------------------------------------------------------- #
echo "Rendering site..."
quarto render
