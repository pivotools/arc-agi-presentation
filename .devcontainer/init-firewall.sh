#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, and pipeline failures
IFS=$'\n\t'       # Stricter word splitting

IPSET_NAME="allowed-domains"
IPV4_CHAIN="CL_ALLOWED_OUTPUT_V4"
IPV6_CHAIN="CL_ALLOWED_OUTPUT_V6"
IPV6_POLICY_MODE="${IPV6_POLICY_MODE:-drop_all}" # values: drop_all, allowlist

reset_v4_chain() {
    iptables -N "$IPV4_CHAIN" 2>/dev/null || true
    iptables -F "$IPV4_CHAIN"
    while iptables -C OUTPUT -j "$IPV4_CHAIN" >/dev/null 2>&1; do
        iptables -D OUTPUT -j "$IPV4_CHAIN"
    done
    iptables -I OUTPUT 1 -j "$IPV4_CHAIN"
}

reset_v6_chain() {
    ip6tables -N "$IPV6_CHAIN" 2>/dev/null || true
    ip6tables -F "$IPV6_CHAIN"
    while ip6tables -C OUTPUT -j "$IPV6_CHAIN" >/dev/null 2>&1; do
        ip6tables -D OUTPUT -j "$IPV6_CHAIN"
    done
    ip6tables -I OUTPUT 1 -j "$IPV6_CHAIN"
}

reset_v4_chain
reset_v6_chain

has_ipv6_connectivity() {
    ip -6 route show default | grep -q '.'
}

# Build/refresh IPv4 allowlist ipset in an idempotent way.
ipset create "$IPSET_NAME" hash:net -exist
ipset flush "$IPSET_NAME"

# Fetch GitHub meta information and aggregate + add their IP ranges
echo "Fetching GitHub IP ranges..."
gh_ranges=$(curl -fsS --connect-timeout 5 --max-time 20 --retry 2 --retry-delay 1 https://api.github.com/meta)
if [ -z "$gh_ranges" ]; then
    echo "ERROR: Failed to fetch GitHub IP ranges"
    exit 1
fi

if ! echo "$gh_ranges" | jq -e '.web and .api and .git' >/dev/null; then
    echo "ERROR: GitHub API response missing required fields"
    exit 1
fi

echo "Processing GitHub IPs..."
while read -r cidr; do
    if [[ ! "$cidr" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$ ]]; then
        echo "ERROR: Invalid CIDR range from GitHub meta: $cidr"
        exit 1
    fi
    echo "Adding GitHub range $cidr"
    ipset add "$IPSET_NAME" "$cidr" -exist
done < <(echo "$gh_ranges" | jq -r '(.web + .api + .git + .packages)[]' | grep -v ':' | sort -u)

# Resolve and add other allowed domains
for domain in \
    "archive.ubuntu.com" \
    "registry.npmjs.org" \
    "api.github.com" \
    "api.anthropic.com" \
    "sentry.io" \
    "statsig.anthropic.com" \
    "statsig.com" \
    "marketplace.visualstudio.com" \
    "pkg.julialang.org" \
    "us-east.pkg.julialang.org" \
    "eu-central.pkg.julialang.org" \
    "storage.julialang.net" \
    "conda.anaconda.org" \
    "repo.anaconda.com" \
    "repo.prefix.dev" \
    "conda-mapping.prefix.dev" \
    "pypi.org" \
    "files.pythonhosted.org" \
    "github.com" \
    "objects.githubusercontent.com" \
    "github-cloud.githubusercontent.com" \
    "vscode.blob.core.windows.net" \
    "pkg.julialang.org" \
    "update.code.visualstudio.com"; do
    echo "Resolving $domain..."
    ips=$(dig +noall +answer A "$domain" | awk '$4 == "A" {print $5}')
    if [ -z "$ips" ]; then
        echo "ERROR: Failed to resolve $domain"
        exit 1
    fi

    while read -r ip; do
        if [[ ! "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            echo "ERROR: Invalid IP from DNS for $domain: $ip"
            exit 1
        fi
        echo "Adding $ip for $domain"
        ipset add "$IPSET_NAME" "$ip" -exist
    done < <(echo "$ips")
done

# AWS S3 CIDR ranges for GitHub LFS storage (github-cloud.s3.amazonaws.com).
# DNS resolution is insufficient because S3 redirects uploads to different IPs
# than what the domain resolves to. These ranges cover the known S3 prefixes
# used by GitHub LFS.
echo "Adding AWS S3 ranges for GitHub LFS..."
for cidr in \
    "3.5.0.0/19" \
    "16.15.0.0/16" \
    "52.216.0.0/15" \
    "54.231.0.0/16"; do
    echo "Adding S3 range $cidr"
    ipset add "$IPSET_NAME" "$cidr" -exist
done

# Get host IP from default route
HOST_IP=$(ip route | grep default | cut -d" " -f3)
if [ -z "$HOST_IP" ]; then
    echo "ERROR: Failed to detect host IP"
    exit 1
fi

HOST_NETWORK=$(echo "$HOST_IP" | sed "s/\.[0-9]*$/.0\/24/")
echo "Host network detected as: $HOST_NETWORK"

reset_v4_chain

# IPv4 egress allow rules.
iptables -A "$IPV4_CHAIN" -o lo -j ACCEPT
iptables -A "$IPV4_CHAIN" -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A "$IPV4_CHAIN" -p udp --dport 53 -j ACCEPT
iptables -A "$IPV4_CHAIN" -p tcp --dport 53 -j ACCEPT
iptables -A "$IPV4_CHAIN" -p tcp --dport 22 -j ACCEPT
iptables -A "$IPV4_CHAIN" -d "$HOST_NETWORK" -j ACCEPT
iptables -A "$IPV4_CHAIN" -m set --match-set "$IPSET_NAME" dst -j ACCEPT
iptables -A "$IPV4_CHAIN" -j REJECT --reject-with icmp-admin-prohibited

IPV6_ACTIVE=false
if command -v ip6tables >/dev/null 2>&1 && has_ipv6_connectivity; then
    IPV6_ACTIVE=true
    reset_v6_chain
    ip6tables -A "$IPV6_CHAIN" -o lo -j ACCEPT
    ip6tables -A "$IPV6_CHAIN" -m state --state ESTABLISHED,RELATED -j ACCEPT
    ip6tables -A "$IPV6_CHAIN" -p udp --dport 53 -j ACCEPT
    ip6tables -A "$IPV6_CHAIN" -p tcp --dport 53 -j ACCEPT
    if [ "$IPV6_POLICY_MODE" = "allowlist" ]; then
        # TODO: extend with an IPv6 allowlist when required.
        :
    fi
    ip6tables -A "$IPV6_CHAIN" -j REJECT --reject-with icmp6-adm-prohibited
else
    echo "IPv6 firewall checks skipped (no ip6tables or no default IPv6 route)."
fi

echo "Firewall configuration complete"
echo "Verifying firewall rules..."
if curl -4 --connect-timeout 5 https://example.com >/dev/null 2>&1; then
    echo "ERROR: Firewall verification failed - was able to reach https://example.com over IPv4"
    exit 1
else
    echo "Firewall verification passed - unable to reach https://example.com over IPv4 as expected"
fi

if [ "$IPV6_ACTIVE" = true ]; then
    if curl -6 --connect-timeout 5 https://example.com >/dev/null 2>&1; then
        echo "ERROR: Firewall verification failed - was able to reach https://example.com over IPv6"
        exit 1
    else
        echo "Firewall verification passed - unable to reach https://example.com over IPv6 as expected"
    fi
fi

# Verify GitHub API access
echo "Resolved IPv4 for api.github.com: $(dig +short A api.github.com | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
if ! curl -4 --connect-timeout 5 https://api.github.com/zen >/dev/null 2>&1; then
    echo "ERROR: Firewall verification failed - unable to reach https://api.github.com over IPv4"
    exit 1
else
    echo "Firewall verification passed - able to reach https://api.github.com over IPv4 as expected"
fi

if [ "$IPV6_ACTIVE" = true ] && [ "$IPV6_POLICY_MODE" = "allowlist" ]; then
    if ! curl -6 --connect-timeout 5 https://api.github.com/zen >/dev/null 2>&1; then
        echo "ERROR: Firewall verification failed - unable to reach https://api.github.com over IPv6"
        exit 1
    else
        echo "Firewall verification passed - able to reach https://api.github.com over IPv6 as expected"
    fi
fi
