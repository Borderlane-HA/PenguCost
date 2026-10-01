#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="${PENGUCOST_VERSION:-latest}"
INSTALL_DIR="${PENGUCOST_DIR:-/opt/pengucost}"
IMAGE="ghcr.io/borderlane-ha/pengucost:${VERSION}"
if ! command -v docker >/dev/null 2>&1; then echo "Docker is required. Install Docker Engine first or use the Proxmox installer." >&2; exit 1; fi
compose(){ if docker compose version >/dev/null 2>&1; then docker compose "$@"; elif command -v docker-compose >/dev/null 2>&1; then docker-compose "$@"; else echo "Docker Compose is required." >&2; exit 1; fi; }
mkdir -p "$INSTALL_DIR"
cat > "$INSTALL_DIR/compose.yml" <<YAML
services:
  pengucost:
    image: ${IMAGE}
    container_name: pengucost
    restart: unless-stopped
    ports: ["8080:8080"]
    volumes: ["pengucost_data:/data"]
    environment: ["TZ=Europe/Berlin"]
    security_opt: ["no-new-privileges:true"]
    cap_drop: ["ALL"]
volumes:
  pengucost_data:
YAML
cd "$INSTALL_DIR"
compose -f compose.yml pull
compose -f compose.yml up -d
echo "PenguCost is running on http://$(hostname -I | awk '{print $1}'):8080"
