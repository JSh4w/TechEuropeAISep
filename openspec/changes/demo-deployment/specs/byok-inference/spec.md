## Purpose

Enables flexible Bring-Your-Own-Key (BYOK) model inference so demo evaluators and developers can supply their own keys across major LLM providers instead of depending on hardcoded Google Gemini keys.

## ADDED Requirements

### Requirement: Dynamic Provider and Key Configuration
The backend SHALL accept model provider configurations (such as OpenAI, Google Gemini, Anthropic, or OpenRouter) dynamically via request payload, HTTP headers, or server environment variables.

#### Scenario: User provides custom OpenAI key in request
- **WHEN** an assessment run is requested with `llm_provider: "openai"` and a valid `llm_api_key`
- **THEN** the system uses the specified OpenAI credentials to execute agent and analysis steps without failing for missing Gemini keys

#### Scenario: Fallback to server environment key
- **WHEN** an assessment run request does not specify an API key
- **THEN** the system falls back to default server environment variables if available, or returns a clear error indicating missing model credentials

### Requirement: Frontend API Key Management
The web UI SHALL provide a settings interface where users can select their inference provider and enter an API key saved locally in browser storage.

#### Scenario: Key persisted across sessions
- **WHEN** a user enters their API key in the UI settings dialog and saves
- **THEN** the key is stored in browser local storage and attached to subsequent run initiation requests

#### Scenario: Test API key connectivity
- **WHEN** a user clicks "Test Key" in the settings dialog
- **THEN** the UI validates connectivity with a minimal test ping and displays the result status
