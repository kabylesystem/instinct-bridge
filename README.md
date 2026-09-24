# Instinct Bridge

Move passwords and authenticator accounts from existing vaults into Instinct, with a clear account of what transferred and what did not.

**Status: working login/TOTP prototype, tested against a real Instinct account with synthetic data on 2026-09-24.** This is not a complete-vault migrator yet. Authy extraction is not implemented or validated. Independent of Instinct, Bitwarden, and Twilio.

The live test confirmed creation, password read-back, complete TOTP configuration, persistence after reload, duplicate prevention, conflict refusal, and cleanup. [Machine-readable evidence](docs/evidence/2026-09-24-e2e.json).

## Run the prototype

Tested on CachyOS/Linux with Python 3.14 and Brave. Other operating systems are not yet verified.

```bash
python3 -m venv .venv
.venv/bin/pip install -e .

# Local preview; no network access or cookies read.
.venv/bin/instinct-bridge tests/fixtures/bitwarden-synthetic.json

# Explicit transfer using only your local Instinct session from Brave.
# Sign in to app.instinct.com in Brave first.
.venv/bin/instinct-bridge tests/fixtures/bitwarden-synthetic.json \
  --apply --brave-session --accept-unofficial-connector
```

The connector runs a separate headless browser and leaves your desktop alone. It uses operations observed in Instinct's own web app, not a published stable API. Session cookies remain in memory; no browser state is exported.

The current source reader accepts **unencrypted Bitwarden JSON**. Encrypted input is not implemented. Keep real exports on your own device and out of Git, issues, and chat. The prototype creates no plaintext intermediate export, but does not delete or secure your original input file.

Items containing notes, URLs, custom fields, passkeys, or other unsupported content are withheld. If any item needs attention, `--apply` stops before transferring anything. It does not silently discard those fields. Vault organization metadata (folders, favorites, IDs, timestamps, permissions) is not migrated. Authenticator labels/issuers are normalized by Instinct; cryptographic parameters are verified.

Only SHA1 / 6 digits / 30 seconds is accepted for live TOTP migration so far. Do not run parallel imports or edit the destination during an import: the observed upsert API has no verified conditional-create primitive. Existing names are checked before writing; conflicting records are withheld and uncertain writes are never retried automatically.

## Verify

```bash
.venv/bin/python -m unittest discover -s tests -v

# Explicit live synthetic test; creates and removes its own unique record.
.venv/bin/python scripts/verify_e2e.py --brave-session
```

This proves stored credentials and TOTP configuration, not a login to an external website or extraction from an actual Authy device. The OTP implementation is checked against [RFC 6238 test vectors](https://www.rfc-editor.org/rfc/rfc6238).

## Intended experience

1. Open the tool locally and select your export.
2. Unlock encrypted exports on your own device.
3. Review accounts, authenticator matches, duplicates, and unsupported data.
4. Transfer selected entries directly to your Instinct vault.
5. Review verified results and any entries needing attention.

The eventual interface is a guided local application with no hosted vault-processing service. The current interface is a CLI; there is no graphical application yet.

## Planned compatibility

| Source | Intended scope | Current evidence |
| --- | --- | --- |
| Bitwarden Password Manager | Supported login fields and embedded default TOTP | Live synthetic round-trip passed |
| Bitwarden Authenticator | Locally stored TOTP accounts in the same JSON schema | Parser test passed; standalone live import not yet tested |
| Standard authenticator export | `otpauth://` embedded in supported JSON | Default TOTP round-trip passed |
| Authy by Twilio | Recoverable TOTP accounts | No official consumer export; separate feasibility work required |
| Google Authenticator, Aegis, 2FAS, Ente | Additional source adapters | Candidates, not implemented |

“Complete” means accounting for every source item and field. It does not mean silently converting unsupported passkeys, attachments, or secure notes into passwords.

## Project documents

- [Product and implementation plan](docs/product-plan.md)
- [Research and compatibility evidence](docs/research.md)
- [Security requirements](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

No real vault files, credentials, session captures, or TOTP seeds belong in this repository or its issues. Examples and demonstrations must use synthetic accounts.
