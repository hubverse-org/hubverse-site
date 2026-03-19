#!/usr/bin/env bash
set -euo pipefail

# --------------------------------------------------------------------------- #
# Install Quarto
# --------------------------------------------------------------------------- #
QUARTO_VERSION="${QUARTO_VERSION:-1.6.40}"
QUARTO_DEB="quarto-${QUARTO_VERSION}-linux-amd64.deb"

echo "Installing Quarto ${QUARTO_VERSION}..."
wget -q "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/${QUARTO_DEB}"
sudo dpkg -i "${QUARTO_DEB}"
rm "${QUARTO_DEB}"

# --------------------------------------------------------------------------- #
# Install yq
# --------------------------------------------------------------------------- #
YQ_VERSION="v4.45.1"
echo "Installing yq ${YQ_VERSION}..."
wget -q "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64" \
    -O /usr/local/bin/yq
chmod +x /usr/local/bin/yq

# --------------------------------------------------------------------------- #
# Install gh CLI
# --------------------------------------------------------------------------- #
echo "Installing gh CLI..."
wget -q https://github.com/cli/cli/releases/download/v2.67.0/gh_2.67.0_linux_amd64.tar.gz
tar xzf gh_2.67.0_linux_amd64.tar.gz
sudo mv gh_2.67.0_linux_amd64/bin/gh /usr/local/bin/gh
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
make contributors
make models
make terminology
make cite

# --------------------------------------------------------------------------- #
# Render site
# --------------------------------------------------------------------------- #
echo "Rendering site..."
quarto render
