#!/usr/bin/env bash
set -Eeuo pipefail
FILE="${1:?Usage: restore.sh BACKUP.tar.gz}"
FILE="$(realpath "$FILE")"
CID="$(docker ps -aqf name=^pengucost$)"
[[ -n "$CID" ]] || { echo "PenguCost container not found" >&2; exit 1; }
VOL="$(docker inspect "$CID" --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}')"
IMAGE="$(docker inspect "$CID" --format '{{.Config.Image}}')"
docker stop pengucost >/dev/null || true
docker run --rm --entrypoint sh -v "$VOL:/data" -v "$(dirname "$FILE"):/backup:ro" "$IMAGE" -c "rm -f /data/pengucost.db /data/.session_secret /data/.fernet_key; tar xzf /backup/$(basename "$FILE") -C /data; mv /data/.pengucost-backup.db /data/pengucost.db; chown -R 10001:10001 /data"
docker start pengucost >/dev/null
echo "Restore completed."
