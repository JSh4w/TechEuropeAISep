## Purpose

Lets each demo visitor run assessments with their own Google AI key, held securely, so the team's own quota is never used and one user's key can never reach another user's run.

## ADDED Requirements

### Requirement: Authenticated access
The API SHALL require a valid Firebase ID token (Google sign-in) on every non-demo endpoint and SHALL identify the caller by `uid`. Verification SHALL check signature, expiry, audience (the Firebase project ID), issuer, and a non-empty `sub`, without needing a service-account credential. When `ALLOWED_EMAILS` is set, only listed emails MAY sign in.

#### Scenario: Unauthenticated request rejected
- **WHEN** a request to `/runs` or `/me/key` has no valid ID token
- **THEN** the API returns 401 and does nothing

#### Scenario: Demo routes stay public
- **WHEN** an unauthenticated visitor opens the demo replay routes
- **THEN** the API serves the recording without requiring sign-in or keys

### Requirement: Locked credential set
The system SHALL accept exactly one credential per user: a Google AI (Gemini) API key, required to start a real run. No other providers, and no user-supplied Modal token, SHALL be accepted.

#### Scenario: Run without a Google key
- **WHEN** a signed-in user with no stored Google key starts a real run
- **THEN** the API returns `401 missing_google_key` and the server's own key is never used

#### Scenario: Unsupported provider
- **WHEN** a request supplies a key for any provider other than Google, or a Modal token
- **THEN** the API rejects it with a validation error

### Requirement: Encrypted key storage
Stored keys SHALL be encrypted with AES-GCM using a per-user key derived from a server master secret, with the `uid` bound as associated data. Plaintext keys SHALL never be returned to the browser after saving.

#### Scenario: Save and read back
- **WHEN** a user saves a Google key and calls `GET /me/key`
- **THEN** the response contains only the last 4 characters and the update time, never the key

#### Scenario: Ciphertext copied between users
- **WHEN** one user's ciphertext is copied into another user's row
- **THEN** decryption fails and the run does not start

#### Scenario: Delete key
- **WHEN** a user deletes a stored key
- **THEN** the row is removed and later runs for that user return `401 missing_google_key`

### Requirement: Per-run key isolation
A run SHALL use only the credentials of its owner. Keys SHALL NOT be held in module-level state, process environment variables, or shared caches, and SHALL NOT appear in plaintext in workflow input, workflow history, logs, traces, or API responses.

#### Scenario: Two concurrent users
- **WHEN** users A and B start runs at the same time with different keys
- **THEN** every model call in A's run uses only A's key and every call in B's run uses only B's key

#### Scenario: Key not in Temporal
- **WHEN** a run completes
- **THEN** the workflow history and `temporal.db` contain no plaintext key and no `"**********"` masked stand-in used as a key

### Requirement: Run ownership
Run endpoints SHALL only serve a run to the `uid` that started it.

#### Scenario: Another user's run id
- **WHEN** a signed-in user requests status, events, decision or result for a run owned by someone else
- **THEN** the API returns 404

### Requirement: Keys panel and first-load prompt
The web UI SHALL provide a config panel (Google key, "Test key" ping) and SHALL show a modal on load, when the signed-in user has no Google key stored, offering **Configure key** or **View demo run**. Detailed UX is deferred.

#### Scenario: No key on first load
- **WHEN** a signed-in user with no stored Google key loads the app
- **THEN** a modal offers to configure the key or view the demo run

#### Scenario: Test key
- **WHEN** a user clicks "Test key"
- **THEN** the UI shows whether a minimal Gemini call succeeded, without displaying the key
