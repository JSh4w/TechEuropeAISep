## Purpose

Eliminates the external Modal GPU dependency by providing an in-process, structured LLM-based classifier and offline heuristic fallback for text and sentiment classification.

## ADDED Requirements

### Requirement: In-process Structured Classification
The system SHALL classify text snippets according to Pydantic schemas using the active LLM provider with structured outputs, eliminating the need for remote Modal calls.

#### Scenario: Paragraph classification via LLM
- **WHEN** news paragraphs or planning quotes require classification against a Pydantic schema
- **THEN** the classifier queries the configured LLM provider and returns validated `Classified` items with confidence scores

### Requirement: Offline Heuristic Classification Fallback
The classifier SHALL provide an immediate rule-based heuristic fallback if no LLM credentials are provided or if external inference fails.

#### Scenario: Fallback on inference error or missing keys
- **WHEN** text classification is requested while offline or without LLM credentials
- **THEN** the classifier falls back to rule-based keyword scoring without crashing the assessment run
