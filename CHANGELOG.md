# Changelog

## 0.1.5

### Fixed
- Replaced the ambiguous ASCII art with a clearly readable `PENGUCOST` installer banner.
- Fixed Proxmox VE 9 / Debian 13 installs where `docker.io` was installed with `--no-install-recommends`, leaving the separately packaged Docker CLI unavailable and causing `docker: command not found` during the image build.
- Docker installation now keeps package recommendations enabled for cross-version Debian compatibility and explicitly verifies the Docker CLI before continuing.
- Added a Docker Compose availability check before the PenguCost source is copied/built.

## 0.1.4

### Changed
- Reworked the Proxmox VE installer to use the guided PenguLab/PenguCoach-style setup flow.
- Added Quick Setup and Advanced Setup before any LXC is created.
- Advanced mode now configures VMID, hostname, CPU, RAM, swap, disk, rootfs/template storage, bridge, DHCP/static IPv4, VLAN, web port and source channel.
- PenguCost source is downloaded and validated before LXC creation, preventing the previous release-bundle 404 from leaving a half-installed container.
- Proxmox deployment now builds the selected source inside the LXC and therefore no longer depends on a GitHub release asset being present.
- Failed installations now offer automatic cleanup of the incomplete LXC.
- Added in-LXC helpers: `pengucost-status`, `pengucost-backup`, `pengucost-restore` and `pengucost-update`.
- Source-based updates create a backup before building/restarting PenguCost.
- Normal runtime remains offline-capable after installation; Internet is only required for installation, updates and optional external AI endpoints.

## 0.1.3
- Added persistent reminder actions: Done, Remind later, and Contract cancelled.
- Added snooze presets for 1/3/7/14/30 days with deadline capping.
- Added two-step confirmation before marking a contract as cancelled.
- Contract cancellation now freezes the current effective term, disables auto-renewal, records the cancellation date, and keeps costs active until term end.
- Added per-reminder event keys so completed reminders can return correctly for later renewal cycles.
- Current dashboard/AI totals now exclude effectively expired non-renewing contracts.
- Added automatic in-place migration from 0.1.2 for cancellation acknowledgement and reminder state storage.

## 0.1.2
- Added configurable colors for all cost categories.
- Category colors are now used in the dashboard donut chart and category badges.
- Added configurable cancellation reminder lead time in Settings.
- Added notification bell with reminder count and a contract reminder center.
- Added separate reminder states for cancellation deadlines, imminent automatic renewals, and already renewed contracts.
- Improved cancellation notice input with common presets plus a custom-day option.
- Added automatic in-place migration from 0.1.1 for the new category color field.

## 0.1.1

- Added effective-dated price history; changing a subscription price no longer rewrites historical periods
- Added support for scheduled future price changes
- Added minimum contract term in months and automatic contract-end calculation
- Added configurable auto-renewal periods in months
- Added effective upcoming contract/cancellation dates for renewed contracts
- Updated annual payment forecast to use the price valid on each payment date
- Added in-place SQLite migration from 0.1.0 and automatic seeding of existing prices into history

## 0.1.0

Initial PenguCost foundation:
- Recurring expense and contract management
- Monthly/yearly normalization
- Contract and cancellation dates
- Account and category assignment
- Interactive dashboard filtering
- Annual payment forecast
- Multi-user local authentication
- Six themes
- Optional OpenAI-compatible AI analysis
- Docker deployment
- Proxmox VE 8/9 installer
- Offline release bundle workflow
- Backup and restore scripts
