# Preview release checklist

- [x] Local graphical review and explicit Authy mapping.
- [x] Portable encrypted Bitwarden reader (PBKDF2 and Argon2id).
- [x] Authy backup reader with independent synthetic encrypted fixtures.
- [x] Host, origin, token, stale-preview and destination-session guards.
- [x] Strict conflict handling and read-back verification.
- [x] Live graphical transfer of independently encrypted synthetic sources, repeat prevention and verified cleanup.
- [x] Desktop/mobile visual checks, 51 unit tests and zero known dependency vulnerabilities in the checked environment.
- [x] Linux standalone executable: demo, capture lifecycle and real synthetic Instinct transfer.
- [x] One transfer button connects, writes, verifies and skips identical repeats.
- [x] A second pass over the 462 existing real logins finished with 462 already present, zero created and zero conflicts.
- [x] One-command source launcher; optional Authy controls; searchable, collapsed large-account review; visible transfer progress.
- [x] Two same-title, same-site synthetic accounts retain distinct usernames/passwords, appear with readable labels, skip on repeat and clean up.
- [x] Consumer UI keeps the main flow to file → review → transfer; encrypted password and optional details appear only when needed.
- [x] Linux tar.gz archive packaging and executable-bit check configured in CI.
- [ ] Validate initial extraction against a real Authy iPhone.
- [ ] Compare migrated keys with codes in the actual Authy app and test real service logins.
- [ ] Independently review security and confirm supported platforms.
- [ ] Before calling it consumer-ready, test a fresh Windows and macOS install through real sign-in and transfer, document OS download warnings, and resolve the Brave-only prerequisite.
- [x] Enable and verify GitHub private vulnerability reporting.
- [x] Publish the repository and Linux preview release with the limits above stated clearly.

## Draft X announcement (not posted)

Je voulais éviter de ressaisir mes logins Bitwarden dans Instinct, alors j'ai fait un outil open source. Import local, aperçu avant transfert, vérification des comptes déjà présents. Preview Linux + Brave pour l'instant : https://github.com/kabylesystem/instinct-bridge
