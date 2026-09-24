# Synthetic fixtures only

All accounts, passwords and keys here are deliberately public test data. Never use them for a real account.

- `bitwarden-synthetic.json`: plaintext fixture with RFC 6238 key.
- `bitwarden-pbkdf2-synthetic.json`, `bitwarden-argon2-synthetic.json`: portable-format encrypted fixtures containing one login without TOTP.
- `authy-encrypted-synthetic.json`, `authy-zero-iv-synthetic.json`: encrypted Authy-format token fixtures paired with that login.

Encryption password for all encrypted fixtures: `SYNTHETIC-export-password`.

Recreate encrypted fixtures using `node scripts/generate_fixtures.mjs` (Node >=24.7). It uses Node/OpenSSL and does not import the application's Python decoder. Fixed salts/IVs are intentional for reproducible **test data only**. These are independent synthetic encodings of inspected formats, not claimed captures from real Bitwarden/Authy apps.
