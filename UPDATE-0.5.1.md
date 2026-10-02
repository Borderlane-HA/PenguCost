# Update 0.5.0 → 0.5.1

The Git-Changes ZIP contains only new or changed files relative to 0.5.0. Copy
its contents into the existing repository, preserving paths. No source files need
deletion. The Full ZIP contains the complete project at 0.5.1.

1. Back up the installation and data volume.
2. Replace the source files, retaining the existing data volume and keys.
3. Rebuild/restart with `docker compose up -d --build`.
4. Confirm version **0.5.1** in the sidebar or `/api/health`.
5. In **Settings → AI profiles**, edit your Ollama profile, choose
   **Automatic / no fixed output limit**, and save. Run a new analysis.

Existing Ollama profiles using the old 8,000-token default switch to Automatic
once during upgrade. Custom limits, including 24,000, remain unchanged, so step 5
is required for those profiles. Later manual settings are retained across restarts.
Other provider defaults and normal AI chat limits remain unchanged.

For a Proxmox installation, commit/upload the changes before running:

```bash
pct exec <VMID> -- /usr/local/sbin/pengucost-update main
```

Use `v0.5.1` instead of `main` only after publishing that tag yourself.

## What Automatic means

PenguCost no longer imposes a fixed output-token cap on Ollama statement requests.
Ollama 0.34.4 converts `max_tokens: -1` into `num_predict: -1`. This does not
increase `num_ctx`, model capacity or hardware resources. Input, reasoning and
output still need to fit the model/runtime context policy. Statement requests
have a 30-minute read timeout per call; connection timeout remains 30 seconds.

If the error arrives immediately even with 24,000 tokens, increasing the output
limit alone is not enough to identify the cause. This version exposes distinct
safe errors for empty answers, reasoning-only answers, missing response choices,
truncation and filtering. Share the new error message when troubleshooting;
there is no need to share private bank statement contents.

The source packages require a frontend rebuild. Docker/Proxmox deployment and a
live Ollama + frozenlab/gemma4-mtp:12b inference were not run in this environment.
