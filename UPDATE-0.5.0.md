# Update 0.4.11 → 0.5.0

The **Git-Changes ZIP** contains only files that are new or changed relative to
the supplied 0.4.11 Full ZIP. Extract and copy/upload its contents into the
existing repository, preserving the paths. No old source files need deletion.
The **Full ZIP** contains the entire source project at 0.5.0.

1. Back up the running installation/data volume first.
2. Replace the source files while keeping the existing data volume and keys.
3. Rebuild and restart:

```bash
docker compose up -d --build
```

For an existing Proxmox installation, commit the update to your repository before
using the normal updater. For the main branch:

```bash
pct exec <VMID> -- /usr/local/sbin/pengucost-update main
```

A published `v0.5.0` tag can be used instead of `main` after you create the release.
New database tables/profile settings are migrated automatically. A frontend
rebuild is necessary because the upload UI and dependencies changed. After the
update, the version in the sidebar and `/api/health` should be **0.5.0**.

Start the feature under **AI Agent → Bank statements / Kontoauszüge**. Configure
a model in Settings → AI profiles if none is enabled. Photos/scans need image
support. The profile's statement output limit defaults to 8,000 tokens and can
be changed under Settings to match your model.

New raw bank files are not retained, results are encrypted and nothing is added
until you review/save a candidate. Existing finance entries and price history
remain. Full restore/import is blocked while AI work is running; restart marks
interrupted AI work as an error instead of leaving it running permanently.

The release ZIPs contain source, not a prebuilt offline Docker image. An initial
source build needs npm/pip access; an offline runtime with a local AI endpoint
is supported after building/installing the image.

See `CHANGELOG.md`, `docs/STATEMENT-ASSISTANT.md` and
`docs/PROJECT-REVIEW-0.5.0.md` for behavior, validation and remaining improvements.
