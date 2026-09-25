# Distribution decision

## Choice

Distribute Instinct Bridge as a **local desktop app with a browser interface**. The user downloads one executable, opens it, chooses a Bitwarden export, reviews the logins and transfers them. The command-line interface remains available for developers. A future Vercel site could explain the tool and link to releases, but must not process vault exports.

## Why the importer is local

The current connector reads the user's existing Instinct session from Brave on their own computer and performs the transfer in a separate headless browser. The optional Authy capture also needs a temporary connection from the iPhone to a service on the user's local network. A Vercel Function cannot read the user's local Brave session or serve as that LAN endpoint. Moving the transfer server to Vercel would require a new authentication mechanism and would send vault data through another hosted service. A static Vercel page could keep file decryption in the browser, but it still could not complete this connector's authentication and phone capture without a local helper or browser extension. This is an inference from the implemented architecture, not a claim that web-based import is impossible in general.

Bitwarden distinguishes password-protected encrypted exports from account-restricted backups; the bridge accepts the former and unlocks them locally. Vercel Functions also impose a [4.5 MB request/response body limit](https://vercel.com/docs/functions/limitations), which a hosted importer would need to design around for larger exports. See [Bitwarden's encrypted export guide](https://bitwarden.com/help/encrypted-export/).

## Release path

1. **Current preview:** Linux x86_64 + Brave. CI builds a standalone executable and a tar.gz archive whose executable permission is preserved. Synthetic end-to-end checks and a real login migration were performed. This can be used without development tools, but downloading an archive and signing in through Brave still creates friction for nontechnical users. Other platforms and browsers are not claimed.
2. **Public GitHub release:** attach the archive and SHA-256 checksums directly to a release, so users do not need to find a CI artifact or install Python. Keep the code, install instructions, exact supported scope and synthetic evidence in the repository.
3. **Broader support:** build and test app downloads on clean macOS and Windows machines, including real Instinct sign-in and transfer, OS download warnings, and the path for users who do not already use Brave. Do not infer working imports from a successful build alone. Validate Authy extraction on a real iPhone and arrange an independent security review before advertising general-purpose vault migration.

The GitHub repository remains private until Kusaila approves publication. No Vercel deployment is needed for the importer.
