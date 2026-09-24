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

The [official homepage](https://instinct.com/) describes the assistant, but does not expose an import specification there. Opening `https://app.instinct.com/vault` in the user's regular Brave profile redirects to the SMS login page. Direct anonymous HTTP fetching returned 403. No authenticated destination schema has been inspected.

[Rohan Adwankar's firsthand investigation](https://rohanadwankar.github.io/posts/platforms.html) reports an internal `tools vault` namespace with import-related capabilities and a GraphQL tool-execution bridge. This is a lead for investigation, not an authenticated public client contract. Do not reuse a sandbox's privileged identity or assume these operations are callable from a community app.

[OpenInstinct](https://github.com/Merit-Systems/OpenInstinct) is a separate project. Its vault implementation does not establish compatibility with the hosted Instinct product.

## Search coverage

Four GitHub discovery passes were run: direct repository keywords (`instinct vault import`), established export tools (`authenticator export stars:>250`), the `authy` topic, and code mentioning both `api.instinct.com` and `vault`. These returned format/extraction candidates and firsthand research; no ready-made compatible bridge was identified in those searches. This is not proof that none exists.

## Evidence to collect next

- Actual Instinct import UI, record types and TOTP support.
- Whether a native Bitwarden import has already shipped.
- A synthetic end-to-end transfer and read-back.
- Current Authy export feasibility on the devices the first release will support.
