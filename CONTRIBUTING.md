# Contributing

The project has a tested login/default-TOTP connector based on operations observed in Instinct's web client. A local graphical interface, portable encrypted Bitwarden input, and an Authy backup reader are implemented. Actual Authy phone extraction and additional source types remain open. Please avoid implementing guessed endpoints.

Contributions should document their format/version assumptions, reuse established libraries where possible, and include synthetic test fixtures. Never use a production vault as a fixture, even with some fields removed.

For each adapter, cover unsupported data explicitly and ensure failed imports cannot appear successful. For transport changes, test partial writes, lost responses, authentication expiry, and duplicate prevention.

Do not claim a source, operating system, or destination capability is supported until the complete user flow has been tested. Third-party source reuse requires compatible licensing and attribution.
