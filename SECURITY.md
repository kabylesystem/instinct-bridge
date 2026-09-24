# Security requirements

This is a design document for an unimplemented tool, not a claim of an audited implementation.

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
