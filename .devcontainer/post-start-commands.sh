#!/bin/bash
set -euo pipefail

CONTAINER_WORKSPACE_FOLDER="${containerWorkspaceFolder:-$(cd "$(dirname "$0")/.." && pwd)}"
SETUP_MARKER="/usr/local/share/devcontainer/.post-create-complete"

if [ -f "${SETUP_MARKER}" ]; then
    echo "=== Reapplying Claude firewall hardening ==="
    bash "${CONTAINER_WORKSPACE_FOLDER}/.devcontainer/init-firewall.sh"
else
    echo "=== Skipping firewall until post-create provisioning completes ==="
fi

export IS_SANDBOX=1
