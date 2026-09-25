# Authy on iPhone

## What is automatic

Once a usable token export is available, Instinct Bridge decrypts it locally, suggests matches, lets you confirm pairings, transfers selected keys, and verifies the stored TOTP configuration. A six-digit code cannot substitute for its underlying secret. Your backup password is different from the six-digit code and the app's local unlock PIN.

## Guided iPhone capture (experimental)

[Twilio's consumer documentation](https://help.twilio.com/hc/en-us/articles/19753420684059-Export-or-Import-Tokens-in-the-Authy-app-Not-Supported) says Authy has no in-app import/export. Instinct Bridge implements a local capture based on the inspected [upstream format and sync trigger](https://github.com/valentin-dirken/authy-export/tree/074d46069f827264b58c0ee0737bdb9fe0d07da5). **The transport and parser pass synthetic tests; extraction from a real Authy iPhone remains unvalidated.** USB pairing succeeded during testing, but app storage access was refused. USB trust alone does not export the keys.

1. Put the computer and iPhone on the same trusted Wi-Fi. A phone providing the computer's hotspot is not the verified setup.
2. In the local app, click **Connect Authy on iPhone**. Scan the QR code with the iPhone and download its uniquely named **Instinct Bridge** profile.
3. Install the profile in Settings → Profile Downloaded. Enable its full trust in Settings → General → About → Certificate Trust Settings. [Apple documents this separate approval](https://support.apple.com/en-ie/102390).
4. Under Settings → Wi-Fi → your network → Configure Proxy → Manual, enter the server and port shown by the app. Authentication stays off.
5. Open Authy → Settings → Accounts. Touch the backups switch, then select **Don't Disable** at the confirmation to request a sync. **Never confirm Disable**, delete tokens, uninstall Authy or reset the phone. If that choice is absent, cancel the capture.
6. Compare the number of received keys with the accounts you expect. Enter that count and finish capture. A matching count is a completeness check, not proof of the correct secret.
7. Turn the phone's Wi-Fi proxy **Off** and remove the temporary profile. Enter your Authy backup password in the local app, then review and transfer. Your backup password is not your app PIN or six-digit code.

The proxy rejects other hosts and unpaired clients, verifies upstream TLS, writes no traffic archive, and retains only allowlisted encrypted token fields. During setup it sees Authy network traffic, including authentication material in memory. The initial profile-download URL is a temporary pairing capability: use a trusted LAN and do not share it. The temporary CA private key lives in a private directory (RAM-backed `/dev/shm` on Linux, OS temp elsewhere) and is removed on normal stop. Crashes may leave files; deletion is not secure erasure.

If the phone cannot open the QR page, check guest-network isolation and the computer firewall. Allow only that iPhone to reach the displayed setup and proxy TCP ports; remove those rules afterward. The app does not disable your firewall. Capture automatically stops after 15 minutes; cancel and restart for a fresh QR/profile. Remove any previous profile before retrying.

This is a guided transfer with unavoidable iOS approvals, not a claim of one-click phone extraction. No real Authy keys have yet completed this flow in the published test evidence.

## File accepted by this bridge

Use an encrypted token JSON, not a raw traffic archive. The root is a list or an object with `authenticator_tokens`. Each account includes:

- `unique_id` (or `id`), `name`, optional `issuer`, `digits`;
- `encrypted_seed`, `salt`, `key_derivation_iterations`, and optional hexadecimal `unique_iv`;
- alternatively, `decrypted_seed` from an existing export (already sensitive plaintext).

The reader accepts standard SHA1 / 6 digit / 30 second TOTP only. It rejects malformed data and ambiguous identifiers. Authy's CBC backup format does not provide the authenticated-integrity guarantee of Bitwarden's export; parsing and padding checks are not a cryptographic authenticity guarantee. Keep the encrypted input from a trusted capture, and compare a generated code with Authy before relying on a migrated account.

## Finish and remove temporary access

Stop the capture tool. Set the iPhone Wi-Fi HTTP proxy back to Off. Remove the installed Instinct Bridge profile under Settings → General → VPN & Device Management, and check that its full trust is gone under About → Certificate Trust Settings. Remove the local capture artifacts and proxy CA private key when no longer needed; ordinary file deletion is not guaranteed secure erasure. These settings and removal must be checked on the actual device.

Keep your original Authy access and recovery codes until you have verified real logins. If extraction fails, the supported fallback is to re-enroll each service's 2FA through that service's settings.
