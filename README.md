# Instinct Bridge

A local app with a simple browser interface for moving Bitwarden logins into Instinct.

**Preview 0.6.0 · Linux x86_64 + Brave.** Tested against a real Instinct vault using synthetic credentials and a full login migration. Duplicate account names and later exports are supported. This moves logins and supported TOTP keys, not every Bitwarden item type. **Extraction from an actual Authy iPhone remains unvalidated.** Independent of Instinct, Bitwarden, and Twilio.

![Local account review using 462 synthetic accounts](docs/evidence/desktop-batch-review.png)

## Use the app

The app runs on your computer and opens in your browser. Sign in to [Instinct](https://app.instinct.com/vault) in Brave first. macOS, Windows and other browsers are not yet verified.

For the Linux preview, download `InstinctBridge-linux-x86_64.tar.gz` from the [0.6.0 release](https://github.com/kabylesystem/instinct-bridge/releases/tag/v0.6.0), extract it and open `InstinctBridge`. The archive preserves executable permissions; Python is not needed. This is an unsigned preview build.

1. Export a Bitwarden JSON file, open the app, and choose it. For encrypted exports, choose **Password protected** in Bitwarden; the app shows the password field when needed.
2. Click **Review logins**, check the count, then **Transfer**. You can search or exclude individual accounts if needed.
3. Check the result in Instinct, then click **Quit**. Keep Bitwarden until you have checked real service logins.

Authy is optional and folded away. If you use it, follow the [iPhone guide](docs/authy-iphone.md). Keep Authy installed until real 2FA logins have been checked. **Try demo** uses synthetic data and cannot write to your vault.

## Run from source

For developers with Python 3.12 or newer:

```bash
git clone https://github.com/kabylesystem/instinct-bridge.git
cd instinct-bridge
./run
```

The first run installs dependencies in the repository's local `.venv`, including the optional iPhone capture support. Later runs start directly. `./run --no-open` keeps your browser untouched and prints a private local link. The app binds to `127.0.0.1`; keep the terminal open. The folder name may contain spaces; the relative `./run` command still works.

## Supported scope

| Input | Supported today | Limits |
| --- | --- | --- |
| Bitwarden JSON | Login titles, usernames, passwords, embedded TOTP, and a hostname from the first valid HTTP(S) site URL | The UI transfers credentials despite duplicate titles and reports other fields; strict CLI still withholds items with extra fields |
| Password-protected Bitwarden JSON | PBKDF2-SHA256 and Argon2id decryption, authenticated AES-CBC | Bounded KDF workload; account-restricted export unsupported |
| Authy | Guided iPhone capture or token JSON; local backup decryption; explicit pairing or standalone OTP entries | iOS trust/proxy settings need manual approval; actual phone extraction still unvalidated |
| TOTP | SHA1, 6 digits, 30 seconds | Other algorithms/configurations are withheld |
| Other vault content | Reported for review | Full URLs, notes, cards, attachments, passkeys and organization metadata are not migrated |

Each Instinct login stores its exact username in Instinct's `username` field. New entries also put the site's **hostname** and a readable username hint in the visible entry name when available, plus a stable Bitwarden item ID. This distinguishes two accounts with the same title and site in Instinct's list. The hint is shortened for unusually long usernames; the exact value stays in the username field. Instinct's observed login schema has no URL field, so full URLs and browser autofill associations cannot be preserved. The original URL remains in Bitwarden. A later export can import newly added logins; previously imported IDs are verified and skipped even if their Bitwarden title changed. A changed password, username or 2FA key on an imported ID causes a conflict and is **not** silently overwritten. Conflicts leave that entry untouched while other selected accounts continue. A timeout or unverified write stops the batch. An identical entry imported by an earlier untagged bridge version is recognized by its exact title and credentials. Import passwords and Authy together for pairing. Live continuous sync is not provided: create a fresh Bitwarden export for later changes.

Entries imported before 0.5.1 retain their existing names when reimported; the bridge does not delete and recreate credentials merely to change a label. Their exact usernames remain stored and independently verifiable in Instinct. The visible username hint helps people and agents select an account, but it does not prove how Instinct's assistant chooses credentials for a task.

Password-only and username-only Bitwarden logins are supported. Instinct refuses reveal requests for empty fields, so verification checks the destination's field-presence flag before attempting a read-back. The review shows whether a password is present, never its value.

## Privacy and transfer behavior

Exports are unlocked in local process memory. No analytics, hosted import service, remote assets, or plaintext intermediate exports. Passwords and OTP seeds are excluded from preview responses and logs. Source files are never deleted. Phone capture is opt-in, allows only `api.authy.com`, keeps only encrypted token fields, and expires after 15 minutes. Its temporary setup/proxy ports are LAN-accessible during capture; all other UI endpoints remain loopback-only. Loaded server data expires after 15 minutes of inactivity; managed memory is not securely erased.

The connector reads the Instinct session from Brave and uses a **separate headless browser**. It relies on operations observed in Instinct's own web application, **not a stable public API**. Selected credentials go directly over HTTPS to Instinct, which receives their plaintext values. This does not extend Bitwarden's end-to-end encryption guarantees to Instinct.

Run one importer at a time without concurrent destination edits: the observed upsert API has no verified conditional-create operation. A failed or uncertain write stops the batch; it is never automatically retried. See [security requirements and limitations](SECURITY.md).

## CLI and verification

```bash
# Local preview, without reading a browser session.
.venv/bin/instinct-bridge tests/fixtures/bitwarden-synthetic.json

# Encrypted preview; prompts privately, never takes a password argument.
.venv/bin/instinct-bridge path/to/export.json --encrypted

# Explicit strict transfer, only if all source items are supported.
.venv/bin/instinct-bridge path/to/export.json --encrypted \
  --apply --brave-session --accept-unofficial-connector

.venv/bin/python -m unittest discover -s tests -v

# Optional: creates and cleans up its own synthetic record in your real vault.
.venv/bin/python scripts/verify_e2e.py --brave-session

# Optional: checks two synthetic usernames at the same service, then removes both.
.venv/bin/python scripts/verify_multi_account.py --brave-session
```

The graphical interface provides Authy pairing and account selection. The CLI currently imports Bitwarden only.

[Live connector evidence](docs/evidence/2026-09-24-e2e.json) and [browser + encrypted-source evidence](docs/evidence/2026-09-24-ui-e2e.json) record exact checks. Synthetic encrypted fixtures are generated independently with Node/OpenSSL (`scripts/generate_fixtures.mjs`); their public password is `SYNTHETIC-export-password`. TOTP is checked against RFC 6238 vectors. These checks do not prove a login to every external service or extraction from an iPhone.

## Building the desktop app

Use Python 3.13, install `.[iphone]` and `pyinstaller==6.22.3`, then run `python scripts/build_desktop.py`. Build on the oldest supported Linux distribution; a binary built on CachyOS may require a newer glibc than Ubuntu. The CI build uses Ubuntu 24.04. A SHA-256 checksum accompanies each artifact.

The iPhone extra pins mitmproxy to an inspected upstream commit because the checked stable release constrained several dependencies to versions with published vulnerabilities. See [verification evidence](docs/evidence/2026-09-24-desktop.json). The audit covers recognized dependency versions; it skips the unpublished mitmproxy snapshot and this local project. This remains experimental and needs maintenance.

## Community release

MIT licensed. Please use synthetic accounts in contributions and bug reports. The current preview needs a real-device Authy extraction test and independent security review before claiming broad migration support.

- [Contributing](CONTRIBUTING.md)
- [Why the importer runs locally](docs/distribution.md)
- [Research and source references](docs/research.md)
- [Implementation plan](docs/product-plan.md)
- [Release checklist](docs/release-checklist.md)
