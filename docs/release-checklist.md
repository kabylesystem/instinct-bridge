# Preview release checklist

- [x] Local graphical review and explicit Authy mapping.
- [x] Portable encrypted Bitwarden reader (PBKDF2 and Argon2id).
- [x] Authy backup reader with independent synthetic encrypted fixtures.
- [x] Host, origin, token, stale-preview and destination-session guards.
- [x] Strict conflict handling and read-back verification.
- [x] Live graphical transfer of independently encrypted synthetic sources, repeat prevention and verified cleanup.
- [x] Desktop/mobile visual checks, 28 unit tests and zero known dependency vulnerabilities in the checked environment.
- [ ] Validate initial extraction against a real Authy iPhone.
- [ ] Compare migrated keys with codes in the actual Authy app and test real service logins.
- [ ] Independently review security and confirm supported platforms.
- [ ] Enable and verify GitHub private vulnerability reporting when publishing.
- [ ] Publish the repository/release and the prepared announcement after reviewing the above limits.

## Draft X announcement — not posted

Je construis Instinct Bridge : une app locale pour importer ses identifiants Bitwarden dans Instinct et y associer ses clés 2FA Authy.

Exports chiffrés, sélection des comptes, vérification après transfert. Prototype testé sur Instinct avec des données fictives ; extraction Authy sur iPhone encore à valider.

Code : https://github.com/kabylesystem/instinct-bridge

The repository is currently private; do not announce it as publicly available yet.
