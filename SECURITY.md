# Security

PenguCost is designed primarily for private LAN/VPN deployments.

## Recommendations

- Put Internet-exposed instances behind HTTPS and an access-control layer.
- Keep Proxmox, Docker and PenguCost updated.
- Back up `/data` or the complete LXC regularly.
- Use a strong administrator password.
- Do not expose port 8080 directly to the public Internet.
- Treat the local data volume as sensitive because it contains financial metadata and the local key material used to decrypt a configured AI API key.

## AI

AI is disabled by default. When enabled with an external provider, selected expense metadata is sent to the configured endpoint only after the user explicitly starts an analysis.

## Reporting

For a public repository, add your preferred private vulnerability-reporting contact before the first public release.
