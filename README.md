# Instinct Bridge

Move passwords and authenticator accounts from existing vaults into Instinct, with a clear account of what transferred and what did not.

**Status: feasibility and design. There is no working importer yet.** The Instinct destination contract still needs verification against an authenticated account. This project is independent of Instinct, Bitwarden, and Twilio.

## Intended experience

1. Open the tool locally and select your export.
2. Unlock encrypted exports on your own device.
3. Review accounts, authenticator matches, duplicates, and unsupported data.
4. Transfer selected entries directly to your Instinct vault.
5. Review verified results and any entries needing attention.

The goal is a guided local application with no hosted vault-processing service. The application format and destination integration are not finalized.

## Planned compatibility

| Source | Intended scope | Current evidence |
| --- | --- | --- |
| Bitwarden Password Manager | Logins and embedded TOTP, followed by other supported item types | Documented JSON exports; destination compatibility unverified |
| Bitwarden Authenticator | Locally stored TOTP accounts | Documented JSON export |
| Standard authenticator export | `otpauth://` TOTP accounts | Open format; destination parameters unverified |
| Authy by Twilio | Recoverable TOTP accounts | No official consumer export; separate feasibility work required |
| Google Authenticator, Aegis, 2FAS, Ente | Additional source adapters | Candidates, not implemented |

“Complete” means accounting for every source item and field. It does not mean silently converting unsupported passkeys, attachments, or secure notes into passwords.

## Project documents

- [Product and implementation plan](docs/product-plan.md)
- [Research and compatibility evidence](docs/research.md)
- [Security requirements](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

No real vault files, credentials, session captures, or TOTP seeds belong in this repository or its issues. Examples and demonstrations must use synthetic accounts.
