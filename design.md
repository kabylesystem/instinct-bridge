# Design — Instinct Bridge

## Direction
Local migration workbench. Dark, precise, full-width. Native HTML controls with a small bundled stylesheet and JavaScript; no third-party browser scripts and no hosted backend. Default design chosen within Kusaila's instruction to complete the tool autonomously.

## References inspected
- https://bitwarden.com/help/import-data/ — explicit source formats, clear import flow and discoverable documentation.
- https://1password.com/product/password-manager — strong readable type, generous controls and clear product hierarchy.
- The authenticated Instinct vault — simple record lists and separate credential fields. We keep the user's preferred dark theme.

## Tokens
--background #0c1118; --surface #131b25; --raised #192432; --border #2b394b; --text #eff4fa; --muted #acbbcc; --accent #77afff; --danger #ff9e9e; --success #8ce3bb.
Typography: Noto Sans with a local sans-serif fallback, with 16px body, 40px page title, 20px section titles. No serif, no all-caps labels. Radius 8px. Spacing 8/16/24/32px.

## Components
Full-width header with small line mark; three numbered stages; two source panels; full-width account table; Authy mapping table; review/transfer action bar; inline progress and detailed result rows. Mobile stacks the sources and account rows. No decorative gradients, no emoji icons, no remote assets.

## Motion
120ms color/opacity transitions; reduced-motion respected. CLI/tests never focus a personal browser; the user-launched desktop executable opens its local interface. Background destination work always uses an isolated headless browser.

## Simplest supported flow
Kusaila requested as few clicks as possible: the desktop executable includes dependencies; a single Transfer action connects and verifies. Authy can be used without a Bitwarden file. Phone setup is revealed only on request, with a QR, received-key count, explicit finish and cleanup reminder. iOS trust approvals cannot be represented as automatic. Quit stops the local server and releases its data.
