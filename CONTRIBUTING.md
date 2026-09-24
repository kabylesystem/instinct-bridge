# Contributing

The project is currently validating source formats and the Instinct destination contract. Please avoid implementing guessed endpoints.

Contributions should document their format/version assumptions, reuse established libraries where possible, and include synthetic test fixtures. Never use a production vault as a fixture, even with some fields removed.

For each adapter, cover unsupported data explicitly and ensure failed imports cannot appear successful. For transport changes, test partial writes, lost responses, authentication expiry, and duplicate prevention.

Do not claim a source, operating system, or destination capability is supported until the complete user flow has been tested. Third-party source reuse requires compatible licensing and attribution.
