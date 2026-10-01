#!/usr/bin/env bash
set -Eeuo pipefail

# PenguCost Proxmox VE installer
# Supports PVE 8 and PVE 9. Creates an unprivileged Debian LXC with Docker.
# Normal PenguCost operation is offline after installation; only updates and
# optional external AI endpoints require network access.

REPO="Borderlane-HA/PenguCost"
VMID="${VMID:-$(pvesh get /cluster/nextid 2>/dev/null || echo 120)}"
CT_HOSTNAME="${PENGUCOST_CT_HOSTNAME:-pengucost}"
STORAGE="${STORAGE:-}"
TEMPLATE_STORAGE="${TEMPLATE_STORAGE:-}"
BRIDGE="${BRIDGE:-vmbr0}"
IP_CONFIG="${IP_CONFIG:-ip=dhcp}"
CORES="${CORES:-2}"
MEMORY="${MEMORY:-2048}"
SWAP="${SWAP:-512}"
DISK="${DISK:-8}"
VERSION="${PENGUCOST_VERSION:-latest}"
BUNDLE_PATH="${BUNDLE_PATH:-}"

red(){ printf '\033[31m%s\033[0m\n' "$*"; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
info(){ printf '\033[36m›\033[0m %s\n' "$*"; }

[[ $EUID -eq 0 ]] || { red "Run this script as root on the Proxmox VE host."; exit 1; }
command -v pveversion >/dev/null || { red "This does not look like a Proxmox VE host."; exit 1; }
PVE_MAJOR="$(pveversion | sed -n 's/.*pve-manager\/\([0-9]\+\).*/\1/p' | head -1)"
[[ "$PVE_MAJOR" =~ ^(8|9)$ ]] || { red "Supported Proxmox VE versions: 8.x and 9.x. Detected: ${PVE_MAJOR:-unknown}"; exit 1; }

[[ -n "$STORAGE" ]] || STORAGE="$(pvesm status --content rootdir 2>/dev/null | awk 'NR>1 && $3=="active" {print $1; exit}')"
[[ -n "$TEMPLATE_STORAGE" ]] || TEMPLATE_STORAGE="$(pvesm status --content vztmpl 2>/dev/null | awk 'NR>1 && $3=="active" {print $1; exit}')"

if pct status "$VMID" >/dev/null 2>&1; then red "VMID $VMID already exists."; exit 1; fi

DEBIAN_MAJOR=12
[[ "$PVE_MAJOR" == "9" ]] && DEBIAN_MAJOR=13
info "Detected Proxmox VE $PVE_MAJOR → Debian $DEBIAN_MAJOR LXC"
[[ -n "$STORAGE" && -n "$TEMPLATE_STORAGE" ]] || { red "Could not auto-detect suitable Proxmox storage. Set STORAGE and TEMPLATE_STORAGE manually."; exit 1; }
info "VMID $VMID · ${CORES} vCPU · ${MEMORY} MB RAM · ${DISK} GB · $BRIDGE"

# Locate or download the matching Debian template.
TEMPLATE="$(pveam list "$TEMPLATE_STORAGE" 2>/dev/null | awk -v d="debian-${DEBIAN_MAJOR}-standard" '$1 ~ d {print $1}' | tail -1)"
if [[ -z "$TEMPLATE" ]]; then
  info "Downloading Debian $DEBIAN_MAJOR template (installation step requires Internet access)."
  pveam update
  TEMPLATE_NAME="$(pveam available --section system | awk -v d="debian-${DEBIAN_MAJOR}-standard" '$2 ~ d {print $2}' | tail -1)"
  [[ -n "$TEMPLATE_NAME" ]] || { red "No Debian $DEBIAN_MAJOR template found."; exit 1; }
  pveam download "$TEMPLATE_STORAGE" "$TEMPLATE_NAME"
  TEMPLATE="${TEMPLATE_STORAGE}:vztmpl/${TEMPLATE_NAME}"
fi

info "Creating unprivileged LXC …"
pct create "$VMID" "$TEMPLATE" \
  --hostname "$CT_HOSTNAME" --unprivileged 1 --features nesting=1,keyctl=1 \
  --cores "$CORES" --memory "$MEMORY" --swap "$SWAP" \
  --rootfs "${STORAGE}:${DISK}" --net0 "name=eth0,bridge=${BRIDGE},${IP_CONFIG},type=veth" \
  --onboot 1 --start 1

info "Installing Docker inside the container …"
pct exec "$VMID" -- bash -lc 'export DEBIAN_FRONTEND=noninteractive; apt-get update; apt-get install -y ca-certificates curl docker.io; (apt-get install -y docker-compose-v2 || apt-get install -y docker-compose); systemctl enable --now docker'

TMPDIR="$(mktemp -d)"; trap 'rm -rf "$TMPDIR"' EXIT
if [[ -n "$BUNDLE_PATH" ]]; then
  [[ -f "$BUNDLE_PATH" ]] || { red "Bundle not found: $BUNDLE_PATH"; exit 1; }
  cp "$BUNDLE_PATH" "$TMPDIR/pengucost-offline-amd64.tar.gz"
else
  info "Downloading PenguCost offline release bundle …"
  if [[ "$VERSION" == "latest" ]]; then
    URL="https://github.com/${REPO}/releases/latest/download/pengucost-offline-amd64.tar.gz"
  else
    URL="https://github.com/${REPO}/releases/download/${VERSION}/pengucost-offline-amd64.tar.gz"
  fi
  curl -fL "$URL" -o "$TMPDIR/pengucost-offline-amd64.tar.gz"
fi

pct push "$VMID" "$TMPDIR/pengucost-offline-amd64.tar.gz" /root/pengucost-offline.tar.gz
pct exec "$VMID" -- bash -lc 'mkdir -p /root/pengucost-offline && tar xzf /root/pengucost-offline.tar.gz -C /root/pengucost-offline && chmod +x /root/pengucost-offline/install-offline.sh && /root/pengucost-offline/install-offline.sh'

# Add a tiny update helper. Updates are the one normal operation that needs Internet.
pct exec "$VMID" -- bash -lc "cat > /usr/local/sbin/pengucost-update <<'UPD'
#!/usr/bin/env bash
set -Eeuo pipefail
VERSION=\"\${1:-latest}\"
TMP=\"\$(mktemp -d)\"; trap 'rm -rf \"\$TMP\"' EXIT
if [[ \"\$VERSION\" == latest ]]; then URL='https://github.com/${REPO}/releases/latest/download/pengucost-offline-amd64.tar.gz'; else URL=\"https://github.com/${REPO}/releases/download/\$VERSION/pengucost-offline-amd64.tar.gz\"; fi
curl -fL \"\$URL\" -o \"\$TMP/bundle.tgz\"
tar xzf \"\$TMP/bundle.tgz\" -C \"\$TMP\"
docker load -i \"\$TMP/pengucost-image.tar\"
cp \"\$TMP/compose.offline.yml\" /opt/pengucost/compose.yml
cd /opt/pengucost
if docker compose version >/dev/null 2>&1; then docker compose -f compose.yml up -d; else docker-compose -f compose.yml up -d; fi
UPD
chmod +x /usr/local/sbin/pengucost-update"

sleep 2
IP="$(pct exec "$VMID" -- hostname -I | awk '{print $1}')"
if pct exec "$VMID" -- curl -fsS http://127.0.0.1:8080/api/health >/dev/null; then
  green "PenguCost installation completed."
  echo "  URL:       http://${IP}:8080"
  echo "  Container: $VMID ($CT_HOSTNAME)"
  echo "  Update:    pct exec $VMID -- pengucost-update [version]"
  echo "  Offline:   Core app works without Internet after installation."
else
  red "Container was created, but the PenguCost health check failed."
  exit 1
fi
