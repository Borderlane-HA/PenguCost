#!/usr/bin/env bash
set -Eeuo pipefail
FILE="${1:?Usage: restore.sh BACKUP.tar.gz}"
FILE="$(realpath "$FILE")"
[[ -f "$FILE" ]] || { echo 'Backup file not found' >&2; exit 1; }
CID="$(docker ps -aqf name=^pengucost$)"
[[ -n "$CID" ]] || { echo 'PenguCost container not found' >&2; exit 1; }
VOL="$(docker inspect "$CID" --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}')"
IMAGE="$(docker inspect "$CID" --format '{{.Config.Image}}')"
[[ -n "$VOL" ]] || { echo 'PenguCost data volume not found' >&2; exit 1; }
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
restore_data() {
  docker run --rm --user 0:0 --entrypoint python \
    -v "$VOL:/data" -v "$FILE:/backup.tar.gz:ro" \
    -v "$SCRIPT_DIR/restore-data.py:/restore-data.py:ro" \
    "$IMAGE" /restore-data.py /backup.tar.gz /data "$@"
}
# Validate before stopping the application or modifying existing data.
restore_data --check
WAS_RUNNING="$(docker inspect "$CID" --format '{{.State.Running}}')"
restart_if_needed() {
  if [[ "$WAS_RUNNING" == 'true' ]]; then docker start "$CID" >/dev/null; fi
}
trap restart_if_needed EXIT
if [[ "$WAS_RUNNING" == 'true' ]]; then docker stop "$CID" >/dev/null; fi
restore_data
echo 'Restore completed.'
