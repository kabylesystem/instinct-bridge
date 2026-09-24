# Authy on iPhone

## What is automatic

Once a usable token export is available, Instinct Bridge decrypts it locally, suggests matches, lets you confirm pairings, transfers selected keys, and verifies the stored TOTP configuration. A six-digit code cannot substitute for its underlying secret. Your backup password is different from the six-digit code and the app's local unlock PIN.

## The initial extraction is separate

[Twilio's consumer documentation](https://help.twilio.com/hc/en-us/articles/19753420684059-Export-or-Import-Tokens-in-the-Authy-app-Not-Supported) says Authy does not support in-app import/export. Its server-side migration APIs are not a consumer vault-export API.

An unofficial [iOS capture implementation](https://github.com/valentin-dirken/authy-export/tree/074d46069f827264b58c0ee0737bdb9fe0d07da5) describes recovering encrypted backup tokens by intercepting Authy's sync traffic locally with mitmproxy. We inspected its format and implemented a local reader; **we have not validated capture against a real iPhone**. No proxy or certificate has been installed by Instinct Bridge.

The upstream method requires a computer and iPhone on the same network, temporary manual Wi-Fi proxy settings, and installation plus explicit trust of a local proxy certificate on the phone. This grants that proxy visibility into intercepted HTTPS traffic. The upstream capture can include unrelated traffic and session credentials: do not upload a capture or use it as a public bug report.

Follow the versioned upstream instructions only after reviewing those effects. Do not disable Authy backups, delete tokens, uninstall Authy, or reset the phone to trigger a sync. The documented “Don't Disable” cancellation is materially different from actually switching backups off. If the expected flow is unavailable on your version, stop; this project does not claim it works on every iOS/Authy release.

A USB connection alone does not grant this bridge access to Authy's protected storage. There is no one-click phone extractor in this release.

## File accepted by this bridge

Use an encrypted token JSON, not a raw traffic archive. The root is a list or an object with `authenticator_tokens`. Each account includes:

- `unique_id` (or `id`), `name`, optional `issuer`, `digits`;
- `encrypted_seed`, `salt`, `key_derivation_iterations`, and optional hexadecimal `unique_iv`;
- alternatively, `decrypted_seed` from an existing export (already sensitive plaintext).

The reader accepts standard SHA1 / 6 digit / 30 second TOTP only. It rejects malformed data and ambiguous identifiers. Authy's CBC backup format does not provide the authenticated-integrity guarantee of Bitwarden's export; parsing and padding checks are not a cryptographic authenticity guarantee. Keep the encrypted input from a trusted capture, and compare a generated code with Authy before relying on a migrated account.

## Finish and remove temporary access

Stop the capture tool. Set the iPhone Wi-Fi HTTP proxy back to Off. Remove the installed mitmproxy profile under Settings → General → VPN & Device Management, and check that its full trust is gone under About → Certificate Trust Settings. Remove the local capture artifacts and proxy CA private key when no longer needed; ordinary file deletion is not guaranteed secure erasure. These settings and removal must be checked on the actual device.

Keep your original Authy access and recovery codes until you have verified real logins. If extraction fails, the supported fallback is to re-enroll each service's 2FA through that service's settings.
