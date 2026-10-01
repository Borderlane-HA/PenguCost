#!/usr/bin/env bash
set -Eeuo pipefail

[[ -f /etc/pengucost-maintenance.env ]] && source /etc/pengucost-maintenance.env
REPO="${PENGUCOST_REPO:-Borderlane-HA/PenguCost}"
PORT="${PENGUCOST_PORT:-8080}"
TARGET="${1:-main}"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

if [[ "$TARGET" == latest || "$TARGET" == stable ]]; then
  TARGET=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null | grep -m1 '"tag_name"' | cut -d '"' -f4 || true)
  if [[ -z "$TARGET" ]]; then
    TARGET=$(curl -fsSL "https://api.github.com/repos/${REPO}/tags?per_page=1" | grep -m1 '"name"' | cut -d '"' -f4 || true)
  fi
  [[ -n "$TARGET" ]] || { echo 'Could not resolve latest release/tag.' >&2; exit 1; }
  URL="https://github.com/${REPO}/archive/refs/tags/${TARGET}.tar.gz"
elif [[ "$TARGET" == main ]]; then
  URL="https://github.com/${REPO}/archive/refs/heads/main.tar.gz"
else
  URL="https://github.com/${REPO}/archive/refs/tags/${TARGET}.tar.gz"
fi

free_mb() { df -Pm / | awk 'NR==2 {print $4}'; }
cleanup_build_space() {
  echo 'Cleaning old Docker build cache and unused images ...'
  docker builder prune -af >/dev/null 2>&1 || true
  docker image prune -af >/dev/null 2>&1 || true
  docker container prune -f >/dev/null 2>&1 || true
}
require_build_space() {
  local free
  free=$(free_mb)
  echo "Free disk space for update: ${free} MB"
  if (( free < 2500 )); then
    echo 'Not enough free disk space to build PenguCost safely (at least 2500 MB recommended).' >&2
    echo 'On the Proxmox host enlarge the LXC root disk, for example: pct resize <VMID> rootfs +8G' >&2
    exit 1
  fi
}

cleanup_build_space
require_build_space

mkdir -p /var/backups/pengucost
BACKUP="/var/backups/pengucost/pengucost-preupdate-$(date +%Y%m%d-%H%M%S).tar.gz"
bash /opt/pengucost-src/scripts/backup.sh "$BACKUP"
echo "Backup: $BACKUP"
require_build_space

curl -fL --retry 2 "$URL" -o "$TMP/source.tar.gz"
mkdir -p "$TMP/source"
tar xzf "$TMP/source.tar.gz" -C "$TMP/source" --strip-components=1
SAFE=$(printf '%s' "$TARGET" | tr -cs 'A-Za-z0-9_.-' '-')
IMAGE="pengucost:${SAFE}"
OLD_IMAGE=$(awk '$1=="image:" {print $2; exit}' /opt/pengucost/compose.yml)

cd "$TMP/source"
docker build -f backend/Dockerfile -t "$IMAGE" .
sed -i "s#^[[:space:]]*image:.*#    image: ${IMAGE}#" /opt/pengucost/compose.yml
cd /opt/pengucost
if docker compose version >/dev/null 2>&1; then docker compose up -d; else docker-compose up -d; fi

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    rm -rf /opt/pengucost-src
    mv "$TMP/source" /opt/pengucost-src
    printf '%s\n' "$TARGET" > /opt/pengucost/installed-version
    # Keep the installed helper in sync with the newly installed source.
    if [[ -f /opt/pengucost-src/scripts/pengucost-update.sh ]]; then
      install -m 0755 /opt/pengucost-src/scripts/pengucost-update.sh /usr/local/sbin/pengucost-update
    fi
    docker builder prune -af >/dev/null 2>&1 || true
    docker image prune -af >/dev/null 2>&1 || true
    echo "PenguCost updated to $TARGET"
    echo "Free disk space after cleanup: $(free_mb) MB"
    exit 0
  fi
  sleep 2
done

echo 'Health check failed after update; restoring previous image reference.' >&2
if [[ -n "$OLD_IMAGE" ]]; then
  sed -i "s#^[[:space:]]*image:.*#    image: ${OLD_IMAGE}#" /opt/pengucost/compose.yml
  cd /opt/pengucost
  if docker compose version >/dev/null 2>&1; then docker compose up -d; else docker-compose up -d; fi
fi
echo "Data backup kept at: $BACKUP" >&2
exit 1
