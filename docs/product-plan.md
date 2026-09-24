# Product plan

## Outcome

A community tool that lets an ordinary user migrate supported credentials into Instinct without manually re-entering each account. Intended distribution: open-source GitHub repository, clear installation instructions, reproducible releases, and an X launch with a synthetic-data demonstration.

Working name: Instinct Bridge. Application format: implemented local guided application, chosen within the authorized autonomous build. No LLM is needed to process credentials or match accounts.

## Resolve the destination first

Inspect the authenticated Instinct Vault UI and its actual import/add-account flow. Record:

- Supported record types, required fields, limits, and import formats.
- Whether a native bulk import already solves the Bitwarden part.
- TOTP import support: shared secret or URI, algorithms, digits, period, issuer, account label.
- Authentication lifetime and how a local application can use an explicitly authenticated session.
- Encryption boundary: what the browser encrypts, what the server receives, and whether a reviewed library is required.
- Response meaning, record read-back, duplicate behavior, and retry semantics.

Prefer native import. If it is insufficient, compare a browser extension using the current session with an application connector. An observed private endpoint is not a supported public API; its version and breakage risk must be documented.

Do not invent GraphQL operations or assume another project's OpenInstinct API belongs to Instinct. Do not deliver raw credentials through the assistant's conversation or email.

## Source ingestion

Use mature format parsers and cryptographic libraries where their license and architecture fit. Prefer password-protected Bitwarden JSON for portable encrypted inputs. Reject account-restricted encrypted exports with an actionable explanation until there is a reviewed supported path.

Keep the source immutable. Build an in-memory normalized inventory that preserves original field ownership and reports unknown fields. Treat all names, notes, URLs, and JSON as untrusted data: no execution, HTML interpretation, or fetching an embedded URL during parsing.

Bound file size, nesting, item counts, archive expansion, and KDF work before consuming resources. Any ZIP support needs path-traversal and decompression-bomb defenses.

## Authenticator matching

Preserve algorithm, digits, period, issuer, account, and secret. Do not coerce an unsupported variant into a six-digit SHA-1/30-second token. Detect HOTP and vendor-specific formats and report them separately.

Match by explicit account identity and service evidence. Multiple accounts at one domain are a review case. Never merge based on a domain alone. Compare TOTP configuration, not merely one coincidentally equal generated code. Use published RFC test vectors to verify generation.

Authy is a dedicated adapter track. Evaluate current maintained tools and supported device conditions before offering a flow. Do not silently install a trusted interception certificate or alter a phone's backup settings. Availability on one device does not establish general consumer support.

## Transfer and recovery

Present selected records, the destination account, and any dropped or transformed fields before transferring. Source records remain unchanged.

Track success, failure, skipped, and uncertain outcomes independently. A lost response after a write is uncertain; reconcile with the destination before retrying. An interrupted transfer must not duplicate records. Destination read-back should establish what was stored, with verification limits stated.

Keep raw credentials out of reports and logs. An optional resumable state must be encrypted and avoid storing secrets when opaque record identifiers suffice. Even identifiers and counts can be private metadata.

## Build sequence and acceptance

1. **Destination proof:** transfer a clearly labeled synthetic login and synthetic TOTP through a verified path; read them back and check behavior. No real-vault bulk transfer during discovery.
2. **Offline source core:** parse supported exports, preserve inventory, identify unsupported fields, and validate TOTP. Test malformed inputs, wrong passwords, tampered encryption, duplicates, and ambiguous matches.
3. **Guided interface:** choose source → unlock → review → connect → transfer → results. English documentation for community distribution; French onboarding can share the same flow.
4. **Robust transfer:** partial failure, rate limits, session expiry, cancellation, uncertain writes, and resumption.
5. **Release:** installation tested on each claimed OS, dependency/license review, synthetic demo, compatibility matrix, security contact, versioned release and changelog. Only claim the platforms and formats actually tested.

## Current implementation — Preview 0.4

Local UI, encrypted Bitwarden PBKDF2/Argon2id input, Authy token decryption, explicit pairing, standalone OTP records, metadata-only preview and destination-session guards are implemented. A single transfer button connects and verifies selected credentials. A Linux standalone executable includes guided, temporary Authy capture; iOS approvals remain manual.

45 tests cover parsing, crypto, web authorization, capture boundaries and cleanup. The UI preview accepts duplicate Bitwarden titles, adds a safe site hostname to each target label, and uses source item IDs to skip identical records on later exports. Conflicting changes are not overwritten. Real Instinct synthetic transfer/read-back/repeat/conflict/cleanup pass, including duplicate-title records. See docs/evidence. One real source login was transferred in an earlier targeted test; the user's full export has only been previewed, not imported. USB pairing is validated, but Authy storage is inaccessible and actual phone extraction remains pending. Full-vault migration, other authenticators and cross-platform runtime support are not delivered.
