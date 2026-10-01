#!/usr/bin/env bash
set -Eeuo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${PENGUCOST_DIR:-/opt/pengucost}"
if ! command -v docker >/dev/null 2>&1; then echo "Docker Engine is required." >&2; exit 1; fi
compose(){ if docker compose version >/dev/null 2>&1; then docker compose "$@"; elif command -v docker-compose >/dev/null 2>&1; then docker-compose "$@"; else echo "Docker Compose is required." >&2; exit 1; fi; }
mkdir -p "$INSTALL_DIR"
docker load -i "$BASE/pengucost-image.tar"
cp "$BASE/compose.offline.yml" "$INSTALL_DIR/compose.yml"
cd "$INSTALL_DIR"
compose -f compose.yml up -d
echo "PenguCost started. No Internet connection is required for normal operation."
