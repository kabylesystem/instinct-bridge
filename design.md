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

## Scope decision — 2026-09-25
Kusaila prioritized the practical migration of logins, passwords and their sites over unsupported vault record types. The review table shows source title, hostname and username; a stable Bitwarden ID in the destination name distinguishes duplicate titles and enables later reimports. The full URL is not represented by Instinct's login schema, so the UI states this limitation before transfer. Avoid presenting partial metadata warnings as if they blocked a credential that is otherwise ready.

## Launch usability — 2026-09-25
The project lives under a directory containing a space. Give shell instructions as a short command available on `PATH`, or as a relative path after changing into the repository. Never give an unquoted absolute path with spaces as the primary launch command. Verify launch commands in Kusaila's actual fish shell before handing them over.

## Large-vault usability — 2026-09-25
The primary action must stay visible above the account table. Fold the list by default for large exports, show the selected total near the action, and let users search and deselect individual entries on demand. Keep Authy setup behind an optional disclosure. Show count-only progress throughout a transfer so long batches are understandable without exposing credentials.

## Multi-account identity — 2026-09-25
Kusaila asked whether Instinct can distinguish different usernames at the same service. Its list displays entry names but not the stored username. New migration names therefore include a readable username hint alongside the hostname and stable source ID; exact usernames stay in the native field. Preserve already imported entries on repeat instead of rewriting or deleting them merely to update a label. Do not claim this proves the assistant's own account-selection behavior.

## Password visibility — 2026-09-25
The review must distinguish a credential with a saved password from a passwordless login. Show presence and totals without sending password values to the browser preview. Keep plaintext password verification in the background transfer path; the results column describes transfer state, not source content.

## Consumer path — 2026-09-25
Kusaila wants a B2C interface with as little small explanatory text as possible. Keep the importer local with a browser UI: one file chooser, a password field revealed only for encrypted Bitwarden exports, a short review summary, and one transfer action. Authy, export help, unsupported-field details and the full account list live in disclosures. Every visible line should teach something new; remove repeated headings, status notices and footer copy. Keep the credential scope and unofficial Instinct connection visible before transfer. Preserve the dark, full-width tokens above, with no hosted processing or remote assets. A packaged GitHub release archive is the consumer download; the CLI/source launcher is for developers.

Kusaila's audience is nontechnical. A Linux-only archive that also requires Brave is a limited preview, not a broadly accessible consumer release. Do not call the product "one click for everyone" until clean-machine installation and actual transfer are verified on the supported mainstream platforms, including the browser sign-in path and OS download warnings. Keep download instructions and release claims specific to the platforms tested.
