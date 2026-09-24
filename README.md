# Instinct Bridge

A local app to move Bitwarden logins and recoverable Authy 2FA keys into Instinct, with account selection, explicit pairing, and verification after transfer.

**Preview 0.5.0.** Tested against a real Instinct vault using synthetic credentials and a full login migration. The UI accepts Bitwarden logins with duplicate titles and supports repeat imports from later exports. It is a login/TOTP bridge, not a complete-vault migration tool. **Extraction from an actual Authy iPhone remains unvalidated.** Independent of Instinct, Bitwarden, and Twilio.

![Local account review using 462 synthetic accounts](docs/evidence/desktop-batch-review.png)

## Run locally

Verified on CachyOS/Linux with Brave: Python source installation and a standalone executable. Other platforms are not yet verified.

For the executable, download the `InstinctBridge-linux-x86_64` artifact from a successful **Desktop build** GitHub Actions run, extract it, allow execution (`chmod +x InstinctBridge`), and open `InstinctBridge`. It opens the local app in your browser. Brave must already be installed and signed in to Instinct. These are unsigned preview builds.

For a source installation with Python 3.12 or newer:

```bash
git clone https://github.com/kabylesystem/instinct-bridge.git
cd instinct-bridge
./run
```

The first run installs dependencies in the repository's local `.venv`, including the optional iPhone capture support. Later runs start directly. `./run --no-open` keeps your browser untouched and prints a private local link. The app binds to `127.0.0.1`; keep the terminal open. Sign in to [Instinct](https://app.instinct.com/vault) in your regular Brave profile before transferring. The folder name may contain spaces; the relative `./run` command still works.

1. Choose a Bitwarden JSON export and click **Review export**. If encrypted, enter the **export password**; it stays local. Portable password-protected exports support PBKDF2 and Argon2id; account-restricted backups are rejected.
2. Check the summary and click **Transfer accounts**. The app connects to Instinct automatically, shows progress and reads each stored credential back to verify it. Open **Review or change individual accounts** only if you want to search, exclude, or inspect individual logins. Password values stay hidden in the preview.
3. Click **Quit** when finished. Keep Bitwarden until you have checked real service logins.

Authy is optional. Open **Also moving Authy codes?** before reviewing if you want to capture keys from an iPhone or load an existing token JSON file. Guided capture needs manual certificate/proxy approval on the phone; compare the received count with Authy, finish capture, remove the proxy/profile, and enter the backup password locally. See the [iPhone guide](docs/authy-iphone.md). Keep Authy installed until real 2FA logins have been checked.

**Try a safe demo** runs a preview that cannot connect to or write to a real vault.

## Supported scope

| Input | Supported today | Limits |
| --- | --- | --- |
| Bitwarden JSON | Login titles, usernames, passwords, embedded TOTP, and a hostname from the first valid HTTP(S) site URL | The UI transfers credentials despite duplicate titles and reports other fields; strict CLI still withholds items with extra fields |
| Password-protected Bitwarden JSON | PBKDF2-SHA256 and Argon2id decryption, authenticated AES-CBC | Bounded KDF workload; account-restricted export unsupported |
| Authy | Guided iPhone capture or token JSON; local backup decryption; explicit pairing or standalone OTP entries | iOS trust/proxy settings need manual approval; actual phone extraction still unvalidated |
| TOTP | SHA1, 6 digits, 30 seconds | Other algorithms/configurations are withheld |
| Other vault content | Reported for review | Full URLs, notes, cards, attachments, passkeys and organization metadata are not migrated |

The UI appends the site's **hostname** and a stable Bitwarden item ID to the Instinct entry name. Instinct's observed login schema has no URL field, so full URLs and browser autofill associations cannot be preserved. The original URL remains in Bitwarden. A later export can import newly added logins; previously imported IDs are verified and skipped even if their Bitwarden title changed. A changed password or 2FA key on an imported ID causes a conflict and is **not** silently overwritten. Conflicts leave that entry untouched while other selected accounts continue. A timeout or unverified write stops the batch. An identical entry imported by an earlier untagged bridge version is recognized by its exact title and credentials. Import passwords and Authy together for pairing. Live continuous sync is not provided: create a fresh Bitwarden export for later changes.

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
```

The graphical interface provides Authy pairing and account selection. The CLI currently imports Bitwarden only.

[Live connector evidence](docs/evidence/2026-09-24-e2e.json) and [browser + encrypted-source evidence](docs/evidence/2026-09-24-ui-e2e.json) record exact checks. Synthetic encrypted fixtures are generated independently with Node/OpenSSL (`scripts/generate_fixtures.mjs`); their public password is `SYNTHETIC-export-password`. TOTP is checked against RFC 6238 vectors. These checks do not prove a login to every external service or extraction from an iPhone.

## Building the desktop app

Use Python 3.13, install `.[iphone]` and `pyinstaller==6.22.3`, then run `python scripts/build_desktop.py`. Build on the oldest supported Linux distribution; a binary built on CachyOS may require a newer glibc than Ubuntu. The CI build uses Ubuntu 24.04. A SHA-256 checksum accompanies each artifact.

The iPhone extra pins mitmproxy to an inspected upstream commit because the checked stable release constrained several dependencies to versions with published vulnerabilities. See [verification evidence](docs/evidence/2026-09-24-desktop.json). The audit covers recognized dependency versions; it skips the unpublished mitmproxy snapshot and this local project. This remains experimental and needs maintenance.

## Community release

MIT licensed. Please use synthetic accounts in contributions and bug reports. The current preview needs a real-device Authy extraction test and independent security review before claiming broad migration support.

- [Contributing](CONTRIBUTING.md)
- [Research and source references](docs/research.md)
- [Implementation plan](docs/product-plan.md)
- [Release checklist](docs/release-checklist.md)
