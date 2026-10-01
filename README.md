# PenguCost 🐧💶

**Know your fixed costs.** PenguCost is a self-hosted, local-first dashboard for subscriptions, contracts, insurance, energy, utilities and every other recurring expense.

The goal is deliberately narrower than a classic budgeting app: **make recurring costs understandable, comparable and actionable** — without turning personal finance into accounting work.

## Highlights

- **Recurring cost management** — monthly, quarterly, half-yearly, yearly or custom billing cycles
- **Normalized cost view** — every item is converted to monthly and yearly equivalents
- **Contract lifecycle** — contract start, minimum term, exact/under-year contract end, cancellation deadline, notice period and configurable renewal period
- **Actionable reminders** — notification bell with configurable lead time, done/snooze/cancel actions and automatic-renewal warnings
- **Accounts & categories** — assign costs to bank accounts/payment methods and custom categories
- **Interactive analysis** — click individual subscriptions/contracts on or off; all totals and charts update immediately
- **Historical price phases** — price changes are effective from a chosen date and never rewrite past months
- **Annual payment forecast** — chart actual expected payment months where a next due date is known, using the price valid at each payment date
- **Multi-user** — local users with Admin and Member roles
- **Themes** — System, Light, Midnight, Nordic, Graphite and Emerald with flash-free theme loading
- **Optional PenguCost AI** — OpenAI-compatible endpoint for savings analysis and contract attention hints
- **Local-first & offline capable** — no CDN, no telemetry, no cloud dependency for the core app
- **Docker & Proxmox** — Docker Compose plus a Proxmox VE 8/9 LXC installer
- **Backup-friendly** — all persistent state lives in one Docker volume

## What PenguCost is for

Examples:

| Expense | Billing | Stored amount | Monthly equivalent | Yearly equivalent |
|---|---:|---:|---:|---:|
| ChatGPT Plus | monthly | €22.90 | €22.90 | €274.80 |
| Car insurance | yearly | €840.00 | €70.00 | €840.00 |
| Electricity service | quarterly | €180.00 | €60.00 | €720.00 |

This makes unlike billing cycles directly comparable while retaining the real payment cycle.

## Screens / Information Architecture

### Overview
- Monthly equivalent total
- Yearly equivalent total
- Number of active contracts
- Deadlines in the next 60 days
- 12-month payment forecast
- Cost breakdown by category
- Interactive expense selector that instantly changes all calculations and charts
- Upcoming cancellation and contract-end timeline

### Costs & Contracts
Each item can contain:
- Name and provider
- Amount and currency
- Billing interval / custom month interval
- Category
- Account / payment route
- Contract start
- Minimum term in months (optional helper)
- Exact contract end, including under-year dates
- Next due date
- Cancellation deadline
- Notice period in days
- Automatic renewal and renewal period in months
- Cancellation acknowledgement date when a contract has actually been cancelled
- Effective-dated price history (old prices remain immutable for past reporting)
- Essential/non-essential marker
- Tags and notes
- Active / paused / cancelled / ended status

### Price history and contract terms
When a recurring cost changes, edit the item, enter the new amount and choose **New price valid from**. PenguCost creates a new price phase instead of overwriting the previous one. Historical charts therefore continue to use the amount that was valid at that time. Future price changes can also be scheduled in advance.

Contracts are date-based rather than calendar-year based. A contract may start or end on any date. If a start date and minimum term are supplied without an explicit contract end, PenguCost calculates the end date automatically. An explicit contract end always wins.


### Reminder center
The bell in the top bar shows the number of contracts that currently need attention. The reminder lead time is configured globally in **Settings → Cancellation reminders**.

Each reminder can be handled directly:
- **Done** hides only the current reminder cycle. A later renewal/cancellation cycle creates a new reminder.
- **Remind later** snoozes the current event for 1, 3, 7, 14 or 30 days, but never beyond the last cancellation day.
- **Contract cancelled** requires confirmation, disables automatic renewal, freezes the current effective contract end and records the cancellation action date. The cost remains active until the actual contract end.

This state is stored in SQLite and therefore survives restarts and upgrades.

### AI Analysis
PenguCost can send only the currently selected cost items to an OpenAI-compatible `/chat/completions` endpoint. Example goals:

> I want to reduce monthly recurring costs by €80 without touching essential contracts.

> Which contracts need attention soon and where are the largest optional costs?

The system prompt explicitly tells the model **not to invent market prices or offers**. External AI is optional; a local OpenAI-compatible service can be used for an entirely local setup.

## Docker installation

```bash
git clone https://github.com/Borderlane-HA/PenguCost.git
cd PenguCost
docker compose up -d --build
```

Open:

```text
http://SERVER-IP:8080
```

On first start, PenguCost asks you to create the first administrator.

## Proxmox VE installation

Supported by the installer:
- Proxmox VE 8.x → Debian 12 LXC
- Proxmox VE 9.x → Debian 13 LXC
- Unprivileged container
- Docker inside the LXC
- 2 vCPU / 2 GB RAM / 8 GB disk defaults
- DHCP by default

Run the installer on the Proxmox host:

```bash
bash scripts/proxmox-install.sh
```

Useful overrides:

```bash
VMID=220 \
STORAGE=local-lvm \
BRIDGE=vmbr0 \
IP_CONFIG='ip=10.10.4.50/24,gw=10.10.4.1' \
MEMORY=2048 \
DISK=8 \
bash scripts/proxmox-install.sh
```

### Offline behavior

The normal first-time Proxmox installation may use Internet access to obtain the Debian template, Docker packages and the PenguCost release bundle. The release bundle contains the complete PenguCost Docker image.

**After installation the PenguCost core application does not require Internet access.**

Network access is only needed for:
1. deliberately requested PenguCost updates, or
2. an optional externally hosted AI endpoint.

If the offline bundle has already been downloaded to the Proxmox host, use:

```bash
BUNDLE_PATH=/root/pengucost-offline-amd64.tar.gz bash scripts/proxmox-install.sh
```


## Build an offline bundle locally

If you want to test the Proxmox installer before publishing a GitHub release, build the bundle on any Docker-capable machine:

```bash
./scripts/build-offline-bundle.sh 0.1.3
```

This creates:

```text
dist/pengucost-offline-amd64.tar.gz
```

Copy that archive to the Proxmox host and run:

```bash
BUNDLE_PATH=/root/pengucost-offline-amd64.tar.gz bash scripts/proxmox-install.sh
```

## Updating a Proxmox installation

Inside the LXC the installer creates:

```bash
pengucost-update latest
```

From the Proxmox host:

```bash
pct exec <VMID> -- pengucost-update latest
```

Or update to a specific release tag:

```bash
pct exec <VMID> -- pengucost-update v0.2.0
```

The persistent `/data` Docker volume is not replaced by an update.

## Backup & restore

```bash
./scripts/backup.sh
./scripts/restore.sh pengucost-backup-YYYYMMDD-HHMMSS.tar.gz
```

For a Proxmox deployment, a normal Proxmox LXC backup additionally protects the whole container.

## AI endpoint configuration

As administrator open **Settings → OpenAI-compatible AI** and configure:

- Base URL, for example `https://provider.example/v1`
- Model name
- API key
- Enable AI

The API key is encrypted before it is stored in the local database. PenguCost itself does not ship a cloud account or relay service.

## Architecture

```text
Browser
  │
  ▼
React + Vite UI
  │  same origin /api
  ▼
FastAPI
  ├── Auth / local users
  ├── Expense & contract API
  ├── Dashboard calculations
  ├── Optional AI client
  └── SQLite /data/pengucost.db
```

The production Docker image contains both the compiled React frontend and the FastAPI backend, so no external web assets are fetched at runtime.

## Repository layout

```text
PenguCost/
├── backend/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── src/
├── scripts/
│   ├── proxmox-install.sh
│   ├── install-docker.sh
│   ├── install-offline.sh
│   ├── backup.sh
│   └── restore.sh
├── docs/
├── .github/workflows/
├── docker-compose.yml
└── README.md
```

## Security choices in the MVP

- Argon2 password hashing
- HTTP-only session cookie
- Local session signing secret generated on first launch
- Local encryption key generated on first launch for stored AI API keys
- Unprivileged Proxmox LXC
- Docker container drops Linux capabilities and enables `no-new-privileges`
- No external frontend assets or telemetry

For Internet-facing installations, place PenguCost behind a trusted HTTPS reverse proxy and an appropriate access policy. The default design assumes a private LAN/VPN deployment.

## Planned next steps

- Home Assistant / SMTP delivery for reminder-center events and upcoming annual payments
- SMTP / Home Assistant webhook notifications
- CSV import/export
- Contract document attachments
- Historical year-over-year comparison and price-change deltas
- Per-user access scopes / household sharing
- OIDC as an optional alternative to local users
- Savings goals with progress tracking
- Optional price/provider research as a separate explicit online feature
- PWA support

## License

PenguCost ships with a source-available personal/non-commercial license in `LICENSE`. Commercial resale, paid hosting and white-label distribution require separate permission.


### Added in 0.1.2
- Configurable category colors used throughout the overview.
- Reminder bell for cancellation deadlines and automatic renewals.
- Configurable reminder lead time in Settings.

### Added in 0.1.3
- Persistent reminder actions: Done, Remind later and Contract cancelled.
- Snooze presets with protection against snoozing past the cancellation deadline.
- Cancellation acknowledgement keeps costs active until the real contract end while disabling auto-renewal.
- Completed/expired contract periods no longer count toward current dashboard totals.
