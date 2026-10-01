# Security

PenguCost is designed primarily for private LAN/VPN deployments.

## Recommendations

- Put Internet-exposed instances behind HTTPS and an access-control layer.
- Keep Proxmox, Docker and PenguCost updated.
- Back up `/data` or the complete LXC regularly.
- Use a strong administrator password.
- Do not expose port 8080 directly to the public Internet.
- Treat the local data volume as sensitive because it contains financial metadata and the local key material used to decrypt configured AI API keys.

## Multi-user privacy

Expenses, contracts, dashboard calculations, reminder actions and AI analysis payloads are scoped to the authenticated user. The administrator can manage user accounts and global account/category templates, but PenguCost does not provide an administrator endpoint for viewing another user's financial records.

Global accounts and categories can be hidden by a member without deleting them for other users. Only an administrator can create or globally delete these shared templates.

## AI

AI profiles are managed only by administrators. Normal users can select enabled profiles for an analysis but do not receive configured base URLs or API-key state from the public profile endpoint. API keys are encrypted at rest using the local PenguCost encryption key.

When an external provider is used, only the authenticated user's explicitly selected expense metadata is sent after that user starts an analysis. Ollama or another local endpoint can be used to keep AI traffic local.

## Reporting

For a public repository, add your preferred private vulnerability-reporting contact before the first public release.
