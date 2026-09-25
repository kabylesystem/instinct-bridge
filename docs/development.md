# Develop Instinct Bridge

## Run from source

Use Python 3.12 or newer. The launcher creates a local virtual environment and installs the optional iPhone capture dependencies on first run.

```bash
git clone https://github.com/kabylesystem/instinct-bridge.git
cd instinct-bridge
./run
```

`./run --no-open` starts the loopback UI without opening a browser and prints its private launch link. Keep the terminal open. The folder name may contain spaces; the relative `./run` command still works.

## CLI

The CLI imports Bitwarden only. The graphical app adds account selection and Authy pairing.

```bash
# Local preview without reading a browser session.
.venv/bin/instinct-bridge tests/fixtures/bitwarden-synthetic.json

# Encrypted preview; prompts privately instead of taking a password argument.
.venv/bin/instinct-bridge path/to/export.json --encrypted

# Strict transfer, only if all source items are supported.
.venv/bin/instinct-bridge path/to/export.json --encrypted \
  --apply --brave-session --accept-unofficial-connector
```

## Verification

```bash
.venv/bin/python -m unittest discover -s tests -v

# Optional: creates, checks and removes synthetic records in your real vault.
.venv/bin/python scripts/verify_e2e.py --brave-session
.venv/bin/python scripts/verify_multi_account.py --brave-session
```

[Live connector evidence](evidence/2026-09-24-e2e.json), [browser and encrypted-source evidence](evidence/2026-09-24-ui-e2e.json) and [same-service account evidence](evidence/2026-09-25-multi-account.json) record the checks. Synthetic encrypted fixtures are generated with Node/OpenSSL (`scripts/generate_fixtures.mjs`); their public password is `SYNTHETIC-export-password`. TOTP is checked against RFC 6238 vectors. These checks do not validate real iPhone extraction or every external service login.

## Build the Linux app

Use Python 3.13, install `.[iphone]` and `pyinstaller==6.22.3`, then run `python scripts/build_desktop.py`. Build on the oldest supported Linux distribution; a binary built on CachyOS may need a newer glibc than Ubuntu. CI builds on Ubuntu 24.04 and checks the executable and archive permissions. SHA-256 checksums accompany the release.

The iPhone extra pins mitmproxy to an inspected upstream commit because its checked stable release constrained several dependencies to versions with published vulnerabilities. See the [desktop evidence](evidence/2026-09-24-desktop.json). The audit covers recognized dependency versions; it skips that unpublished mitmproxy snapshot and this local project. This part still needs maintenance.

See [SECURITY.md](../SECURITY.md) for the connector's trust boundary, repeat-import behavior, session handling and capture limits. The [implementation plan](product-plan.md) tracks unfinished platform and format support.
