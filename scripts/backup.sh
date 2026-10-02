#!/usr/bin/env bash
set -Eeuo pipefail
OUT="${1:-./pengucost-backup-$(date +%Y%m%d-%H%M%S).tar.gz}"
CID="$(docker ps -aqf name=^pengucost$)"
[[ -n "$CID" ]] || { echo "PenguCost container not found" >&2; exit 1; }
VOL="$(docker inspect "$CID" --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}')"
IMAGE="$(docker inspect "$CID" --format '{{.Config.Image}}')"
[[ -n "$VOL" ]] || { echo "PenguCost data volume not found" >&2; exit 1; }
ABS_OUT="$(realpath -m "$OUT")"; OUT_DIR="$(dirname "$ABS_OUT")"; OUT_FILE="$(basename "$ABS_OUT")"; mkdir -p "$OUT_DIR"
docker run --rm -v "$VOL:/data" "$IMAGE" python -c "import sqlite3; src=sqlite3.connect('/data/pengucost.db'); dst=sqlite3.connect('/data/.pengucost-backup.db'); src.backup(dst); dst.close(); src.close()"
docker run --rm --user 0:0 --entrypoint sh -e "BACKUP_NAME=$OUT_FILE" -v "$VOL:/data:ro" -v "$OUT_DIR:/backup" "$IMAGE" -c 'umask 077; tar czf "/backup/$BACKUP_NAME" -C /data .pengucost-backup.db .session_secret .fernet_key' 
docker run --rm --entrypoint sh -v "$VOL:/data" "$IMAGE" -c 'rm -f /data/.pengucost-backup.db'
echo "$ABS_OUT"
