#!/bin/bash
set -e

# Get workspace folder from environment variable or derive from script location
CONTAINER_WORKSPACE_FOLDER="${containerWorkspaceFolder:-$(cd "$(dirname "$0")/.." && pwd)}"

echo "=== Installing system dependencies ==="
apt-get update
echo 'tzdata tzdata/Areas select Europe' | debconf-set-selections
echo 'tzdata tzdata/Zones/Europe select Berlin' | debconf-set-selections
DEBIAN_FRONTEND="noninteractive" apt-get install -y \
    bash-completion \
    ca-certificates \
    curl \
    dnsutils \
    git \
    git-delta \
    git-lfs \
    gnupg \
    iproute2 \
    ipset \
    iptables \
    jq \
    less \
    openssh-client \
    procps \
    python3 \
    python3-pip \
    squashfuse \
    sudo \
    vim \
    wget

echo "=== Setting SSH key permissions ==="
chmod 600 /root/.ssh/key 2>/dev/null || true
chmod 644 /root/.ssh/key.pub 2>/dev/null || true
chmod 600 /root/.ssh/config 2>/dev/null || true

echo "=== Setting up Git goodies ==="
# Configure git completion in bashrc (idempotent)
if ! rg -q "BEGIN: git-completion" ~/.bashrc; then
cat << 'EOF' >> ~/.bashrc
# BEGIN: git-completion
if [ -f /usr/share/bash-completion/completions/git ]; then
    . /usr/share/bash-completion/completions/git
elif [ -f /etc/bash_completion.d/git ]; then
    . /etc/bash_completion.d/git
fi
# END: git-completion
# inform Claude that we are in a sandbox
export IS_SANDBOX=1
EOF
fi

echo "=== Installing claude code ==="
curl -fsSL https://claude.ai/install.sh | bash

echo "=== Enabling Claude firewall hardening ==="
bash "${CONTAINER_WORKSPACE_FOLDER}/.devcontainer/init-firewall.sh"
mkdir -p /usr/local/share/devcontainer
touch /usr/local/share/devcontainer/.post-create-complete

echo "=== Setup complete ==="
