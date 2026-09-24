# Research — 2026-09-24

## Bitwarden

[Vault export documentation](https://bitwarden.com/help/export-your-data/) describes JSON, encrypted JSON, CSV, and individual-vault ZIP exports with attachments. JSON covers more item types than CSV, including cards, identities, passkeys, and SSH keys. Trash and Sends are excluded; organization-owned entries require a separate appropriate export.

[Encrypted exports](https://bitwarden.com/help/encrypted-export/) distinguishes account-restricted exports from portable password-protected exports. Never treat these as interchangeable.

[Authenticator import/export](https://bitwarden.com/help/authenticator-import-export/) documents JSON containing `login.totp` URI values. Locally stored Authenticator codes can be exported there; vault-synced codes must be exported from Password Manager. This gives two concrete starting inputs without requiring a proprietary extraction mechanism.

Reuse candidates: the [official export SDK](https://sdk-api-docs.bitwarden.com/bitwarden_exporters/index.html), [Bitwarden CLI](https://bitwarden.com/help/cli/), and [attie/bitwarden-decrypt](https://github.com/attie/bitwarden-decrypt). These have not been adopted or tested for this project. Their suitability and licenses must be checked before integration.

## Authy

Twilio's [2FA account-token support index](https://help.twilio.com/sections/19752375651355-2FA-Account-Tokens) lists export/import as unsupported. Its [server-side TOTP migration API](https://www.twilio.com/docs/authy/export-totp-secret-seed-for-migrating-to-verify-totp) is not a general export API for a consumer's whole Authy app.

[valentin-dirken/authy-export](https://github.com/valentin-dirken/authy-export) describes a local iOS traffic-capture approach and claims current compatibility after restrictions affected older tools. It is MIT licensed according to its README. We read the workflow; we have not audited its code or reproduced its claims. It requires sensitive device configuration and is not yet an endorsed dependency.

[alexzorin/authy](https://github.com/alexzorin/authy) is a historical Go implementation. Its existence does not establish that its registration/export endpoints still work.

[scito/extract_otp_secrets](https://github.com/scito/extract_otp_secrets) is a maintained Google Authenticator QR-export tool, GPL-3.0 according to GitHub metadata checked today. Useful as a candidate or format reference; copying code into a differently licensed product needs an explicit license decision.

## Instinct

The [official homepage](https://instinct.com/) does not expose an import specification. Anonymous fetching returned 403, but after the user signed in, the actual web client was inspected and exercised in an isolated authenticated headless browser.

Observed endpoint: `https://api.instinct.com/-/api/graphql`. The web client's `useVaultQuery`, `useVaultUpsertMutation`, `useVaultRevealMutation`, and `useVaultDeleteMutation` supply the connector contract. Upsert receives a kind/name and key/value field list. Login fields include `username`, `password`, and `totp`. The server returns the TOTP secret as a normalized `otpauth://` URI, not as the original bare seed. All default cryptographic parameters were verified equal after read-back. These are observed private web operations, not a published supported API.

The actual HTTP save returned 200 without GraphQL errors. A live automated fixture subsequently verified persistence, repeat import, conflict handling and cleanup. See [the report](evidence/2026-09-24-e2e.json). This does not establish Authy extraction or full-vault compatibility.

[Rohan Adwankar's firsthand investigation](https://rohanadwankar.github.io/posts/platforms.html) reports an internal `tools vault` namespace with import-related capabilities and a GraphQL tool-execution bridge. This is a lead for investigation, not an authenticated public client contract. Do not reuse a sandbox's privileged identity or assume these operations are callable from a community app.

[OpenInstinct](https://github.com/Merit-Systems/OpenInstinct) is a separate project. Its vault implementation does not establish compatibility with the hosted Instinct product.

## Search coverage

Four GitHub discovery passes were run: direct repository keywords (`instinct vault import`), established export tools (`authenticator export stars:>250`), the `authy` topic, and code mentioning both `api.instinct.com` and `vault`. These returned format/extraction candidates and firsthand research; no ready-made compatible bridge was identified in those searches. This is not proof that none exists.

## Evidence to collect next

- Actual Authy export feasibility on the user's device, followed by account matching and transfer.
- Other item types and non-default OTP configurations. Portable encrypted inputs now have independent synthetic tests.
- Any native bulk-import feature beyond the inspected vault editor; its absence has not been established.

## Encrypted formats implemented in preview 0.2

Bitwarden encoding was checked against [the SDK encrypted exporter](https://github.com/bitwarden/sdk-internal/blob/main/crates/bitwarden-exporters/src/encrypted_json.rs) and its crypto KDF/key helpers. The portable format derives from the base64 salt text, uses SHA256(salt text) for Argon2id, expands separate enc/mac keys, and authenticates type-2 AES-CBC ciphertext before decrypting. Independent fixtures are encoded with [Node/OpenSSL crypto](https://nodejs.org/api/crypto.html), not with the production Python decoder. They validate format compatibility against that independent encoder, not an actual new Bitwarden export.

Authy token fields and PBKDF2-SHA1/AES-CBC decryption were inspected in [authy-export at commit 074d460](https://github.com/valentin-dirken/authy-export/tree/074d46069f827264b58c0ee0737bdb9fe0d07da5). The reader accepts captured/exported JSON. Preview 0.3 adds its own narrowly scoped capture integration; no third-party capture script is run. Real-device extraction is still unvalidated.

## Preview 0.3 capture and packaging

The integrated proxy uses mitmproxy events to reject unpaired clients and any upstream except `api.authy.com:443`, verifies upstream TLS, and extracts only encrypted token fields from successful sync responses. A private setup nonce pairs the first profile downloader. The 15-minute lifetime is enforced independently of UI polling. Transport boundaries are tested using a real local proxy with synthetic input.

The inspected stable mitmproxy 12.2.3 dependency set produced vulnerability findings in cryptography, h2, msgpack and tornado. The iPhone extra instead pins inspected upstream [commit b506c68](https://github.com/mitmproxy/mitmproxy/tree/b506c68108e287104045333ade476d92c39c275e), whose updated bounds permit the checked fixes. The clean packaging environment audit returned zero known findings for recognized versions. It skipped the unpublished mitmproxy 13.0.0.dev0 snapshot and this local project, so it does not establish their advisory status or provide an independent security audit.

The Linux executable passed a live synthetic Instinct transfer, independent read-back, identical repeat and cleanup. The final rebuild additionally passed desktop/mobile UI and capture-start/quit/closed-port checks. USB pairing on iOS 26.6.1 succeeded; Authy 28.6.2 sandbox access returned InstallationLookupFailed. No Authy keys were received. A capture session expired, and its temporary firewall rules were removed; no bridge profile was present in the installed-profile query.

## Full-vault target capability check — 2026-09-25

A read-only query against the user's authenticated vault reported these native kinds and field keys: `login` (`username`, `password`, `totp`), `card` (`number`, `exp_m`, `exp_y`, `cvv`, `zip`), `address` (`line1`, `line2`, `city`, `state`, `zip`, `country`), `phone` (`number`), and `ssn` (`full`). Synthetic upsert probes for `note`, `secureNote`, `identity`, `sshKey`, and `passkey` failed. A login probe with `notes` and `bitwarden_payload` extra fields also failed. All accepted synthetic probes were deleted; none remains. These private web operations are undocumented and can change.

The official [Bitwarden export reference](https://bitwarden.com/help/export-your-data/) documents cards, identities, secure notes and logins in JSON, plus passkeys and SSH keys; attachments are provided through ZIP export. Trash and Sends are omitted, and a personal export does not include organization-owned items. A single personal JSON snapshot therefore cannot mean literally everything in those categories. A new snapshot is also needed to see later Bitwarden changes; this bridge does not watch the Bitwarden vault live.

The 2026-09-25 local live test did import one strictly supported login item and independently read back its supported values. No other source entries were written. The user's source file remains unchanged.

## Login-focused bridge — Preview 0.4

The observed Instinct login kind has no URL subfield. The bridge therefore extracts only a validated HTTP(S) hostname from Bitwarden `login.uris` for the destination name; URL paths, queries and fragments are not copied into that name. A stable marker based on each Bitwarden item UUID separates duplicate titles and permits idempotent reimports. Existing records with that marker are read back; identical records are skipped, changed records conflict. A legacy unmarked record is skipped only when its title and stored credentials match exactly. No live sync or automatic password update is claimed.

A local dry-run of the user's export admitted every login without writing any of them. A separate live synthetic run created two same-title records with different hostnames/IDs, verified repeat skips, and deleted both test records. The UI synthetic E2E checked single-click creation, independent readback, repeat skip, desktop/mobile layout and cleanup. Authy extraction from the actual iPhone is still unvalidated.

## Empty-field readback — Preview 0.4.1

The observed Instinct API returns a GraphQL error when `revealVaultSubfieldValue` is called for an unpopulated username or password. An initial large transfer had already saved a password-only login when its read-back failed on the empty username. The connector now uses `vaultEntries.fields[].populated` to verify absent values without requesting an unsupported reveal. Live synthetic tests cover password-only and username-only records, repeat import, and cleanup. The interrupted real login batch was resumed; each selected record was either newly created and verified or recognized by read-back. A fresh destination session confirmed the complete set of source IDs and sampled stored credentials. No password values are included in project evidence.

## Same-service accounts — Preview 0.5.1

Two synthetic Bitwarden logins with the same title and hostname but different usernames and passwords were created in the real Instinct vault. Instinct stored two distinct entries, exact read-back matched each account, cross-account comparison failed as expected, both were skipped on repeat, and both were removed. The vault list displayed both entry names but did not display their native username fields. New bridge labels therefore include a shortened, printable username hint plus the existing hostname and stable source ID. A second live test confirmed both usernames were visible in those new labels. [The synthetic report](evidence/2026-09-25-multi-account.json) contains no credentials. Previously imported labels remain unchanged on reimport; this test does not establish how Instinct's assistant selects a credential in an actual task.
