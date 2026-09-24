# Changelog

## 0.6.0 — preview

- Shorter local interface: choose export, review logins, transfer. The export-password field appears only for encrypted Bitwarden files; Authy and detailed account lists stay optional.
- Linux x86_64 tar.gz download preserves the executable permission. The source launcher and CLI remain available for developers.
- Each new login stores its exact username in Instinct and includes a readable username hint, site hostname and stable Bitwarden ID in its entry name. Repeat imports verify and skip existing IDs; conflicts are not overwritten.
- Verified with 51 unit tests, browser checks on desktop/mobile, and synthetic Instinct transfers with read-back and cleanup.

Limits: Linux + Brave is the only verified consumer setup. Instinct's connector uses an unofficial private web API and cannot preserve full URLs or unsupported Bitwarden item types. Real Authy iPhone extraction and the assistant's own account-selection behavior remain unvalidated. Previously imported entry names are not automatically rewritten.
