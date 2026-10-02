# Update 0.5.1 → 0.5.2

The Git-Changes ZIP contains new or changed files relative to 0.5.1. Copy its
contents into your repository, preserving paths. No source files need deletion.
The Full ZIP contains the complete project at 0.5.2.

1. Back up the installation/data volume and retain the existing keys.
2. Replace the source and rebuild: `docker compose up -d --build`.
3. Check version **0.5.2** in the sidebar or `/api/health`.
4. Edit the Ollama AI profile: keep **Automatic / no fixed output limit** and
   use **32,768** for **Ollama: statement context window (tokens)** initially.
5. Start a new analysis; previous failed analyses remain failed.

Existing profiles automatically receive the new context setting. Manual output
limits from prior versions remain unchanged. The login username field is empty.

For Proxmox, upload/commit first, then use your normal updater:

```bash
pct exec <VMID> -- /usr/local/sbin/pengucost-update main
```

Use a `v0.5.2` tag only after publishing that tag yourself.

## Ollama changes

The output cap and context size are different settings. Automatic removes the
fixed prediction cap; it does not itself enlarge context. Statement analysis
now uses native `/api/chat` with `num_ctx`, `num_predict`, JSON output and
`think: false`. Ollama pages are processed one at a time. Increasing context
uses more memory; you can lower it or set 0 for the server default when needed.
The profile base URL can remain `http://<host>:11434/v1`. Reverse proxies must
also permit `/api/chat` at the same configured prefix.

The selected result panel now updates automatically on error/ready, fixing a
polling race. Page progress counts completed extraction requests, not live tokens.
No progress can be counted if the first request fails.

If native Ollama still reports `done_reason=length`, the new message includes
requested context and safe prompt/generated token counts. Share that message,
and run `ollama ps` while analysis is active to inspect the actual CONTEXT and
PROCESSOR columns. Requested context is not proof that the server applied it.
No bank statement contents or model reasoning need to be shared.

## Validation limits

Tests and browser checks use isolated data and model/HTTP fixtures. They do not
prove successful inference on the user's Ollama 0.34.4 + frozenlab/gemma4-mtp:12b
installation. The underlying provider failure has not been reproduced locally.
Docker and Proxmox deployment were not executed here.
