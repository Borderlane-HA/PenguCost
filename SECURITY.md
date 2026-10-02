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

Expenses, contracts, dashboard calculations, reminder actions and AI analysis payloads are scoped to the authenticated user. The administrator can manage user accounts and global account/category templates. Normal application endpoints do not expose another user's financial records; the only deliberate exception is the explicit administrator full-export/full-restore feature documented below.

Global account/category templates can be hidden by a user without deleting them for anyone else. Users may also create private accounts, cards/payment methods and categories that are visible only to themselves. Only an administrator can create, edit or globally delete shared templates; private catalog IDs are revalidated server-side before they can be attached to financial entries.

## AI

AI profiles are managed only by administrators. Normal users can select enabled profiles for an analysis but do not receive configured base URLs or API-key state from the public profile endpoint. API keys are encrypted at rest using the local PenguCost encryption key.

When an external provider is used, only the authenticated user's explicitly selected financial entries, that user's AI conversation history and that user's Brain context are supplied to the model. Selected entry IDs are revalidated server-side before every AI turn. Ollama or another local endpoint can be used to keep AI traffic local.

AI conversations and Brain memory are stored per user in SQLite. A normal administrator cannot browse another user's conversations through the application UI/API; they are included only in the explicit privileged full-instance backup/restore path.

## Reporting

For a public repository, add your preferred private vulnerability-reporting contact before the first public release.
## Export files

Personal user exports contain that user's private recurring-cost and contract data, private account/category catalogs, hidden global-template preferences, AI conversation history and Brain memory. Administrator full exports are more sensitive: they contain all users' data, password hashes and AI API keys in a restorable form. Store full export JSON files like backups or secrets, do not commit them to Git, and transfer them only over trusted channels.

The normal administrator UI still does not expose another user's cost data. The full export is an explicit privileged backup/restore action and should only be used by a trusted instance administrator.

## Financial data isolation

Income entries, expenses, contracts, dashboard selections, reminders and AI payloads are scoped to the authenticated owner. Administrator privileges do not expose another user's financial entries through normal application views; only the explicit full-instance backup/restore path contains all users' data.

## Password management

- Local passwords are stored only as Argon2 hashes.
- Users can change their own password only after confirming the current password.
- Administrators can reset passwords for any local account, including their own, from User management. Password changes/reset invalidate older signed-in sessions for that account.
- Use a unique, sufficiently long password for every PenguCost account.


## Bank statement uploads (0.5.0)

Statement processing explicitly confirms transmission to the selected AI profile.
Text-PDF content or scan/photo pages go to that profile; external providers apply
their own retention policies. Raw uploads are temporary and not retained in the
PenguCost volume. Candidates and source evidence are encrypted with the same
Fernet key used for AI secrets, isolated per user and excluded from portable JSON
exports. Volume backups include encrypted results and matching key material.
Deleting a job discards its results and stops subsequent processing; requests
already received by a provider cannot be recalled. Document contents are treated
as untrusted data, extracted fields and page evidence are validated, and imports
require a separate review action. No model has finance-write tools.
