# Security requirements

These are security requirements and current implementation limits. The prototype has functional tests; it has not received an independent security audit.

## Implemented prototype

The CLI previews locally by default. Transfer requires explicit flags. It reads only Instinct's session cookie from Brave, then uses an isolated headless browser. Neither cookies nor returned secrets are logged or persisted by the connector. Requests go over HTTPS directly to `api.instinct.com`; the observed web client sends field values to that server. This is not an end-to-end encrypted bridge whose destination cannot read its inputs.

The source reader accepts plaintext JSON or portable password-protected Bitwarden JSON, using bounded PBKDF2/Argon2id and verifying HMAC before AES-CBC decryption. Authy backups use the inspected PBKDF2-SHA1/AES-CBC format; that format has no authenticated integrity guarantee. The bridge does not create an intermediate plaintext file, but it cannot protect an already-existing export, OS swap, browser crash dumps, extensions in the source browser, or a compromised machine. Python/browser memory is not securely erased. Browser session reading depends on the third-party `browser-cookie3` library and the local OS key store.

Name conflict checks are client-side. A concurrent writer could race the check because the private upsert API has no verified conditional-create feature. Run one importer at a time with no concurrent edits. Uncertain writes stop the transfer; inspect/reconcile before retrying. A second run verifies an identical existing record and skips it.

The local UI binds to loopback, requires a per-launch bearer token, exact Host and Origin, JSON POST requests, and serves bundled assets under a restrictive CSP. It serializes operations and rejects stale previews and changed destination sessions. It releases loaded server references after 15 idle minutes. Names/usernames remain visible in browser memory until the page is closed; release is not secure erasure. Anyone with access to the launch URL or this OS account can act as the local user. It is a single-user desktop utility, not a shared server.

Authy phone capture is not part of the implemented automatic pipeline. The experimental upstream method requires temporary device trust settings and may capture unrelated traffic. See the [iPhone guide](docs/authy-iphone.md). Never deploy this app to a public host or use a tunnel with real vault data.

## Intended trust boundary

Exports are processed locally. The selected destination is the user's authenticated Instinct vault. Moving credentials there gives Instinct custody of them according to its own architecture and policies; this bridge cannot extend Bitwarden's end-to-end encryption guarantees to another provider.

- No analytics, third-party vault-processing service, or LLM processing of secrets.
- No credentials in chat, email, URLs, command-line arguments, logs, crash reports, or demonstration media.
- No plaintext intermediate files created by default. Do not promise reliable memory erasure in a managed runtime or secure deletion on arbitrary storage.
- No master password sent to Instinct. Unlock exports locally using reviewed cryptographic implementations and verify integrity before accepting plaintext.
- No silent uploads, background synchronization, source deletion, or ambiguous account merges.
- Pin and review dependencies. Bundle assets rather than loading executable scripts from a CDN.
- If a localhost server is chosen, bind to loopback and defend against cross-origin requests, CSRF, DNS rebinding, and unauthorized local sessions.
- If a browser extension is chosen, minimize host permissions and never export the user's session to a hosted service.

## Reporting issues

Never attach a real vault, password, TOTP seed, backup, HAR, or session cookie to an issue. Use synthetic reproductions and sanitized technical details. A private vulnerability-reporting channel must be configured and verified before public release.
