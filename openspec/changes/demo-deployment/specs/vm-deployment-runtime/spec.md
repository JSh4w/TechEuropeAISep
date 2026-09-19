## Purpose

Defines a lightweight, single-host runtime architecture capable of running Temporal, the API server, worker, and web frontend on an Ubuntu virtual machine under 1 GB total memory usage.

## ADDED Requirements

### Requirement: Lightweight Temporal Orchestration
The deployment SHALL utilize the standalone Temporal CLI development server (`temporal server start-dev` with embedded SQLite) rather than multi-container cluster images.

#### Scenario: Standalone Temporal execution
- **WHEN** the Temporal dev server is started with SQLite persistence
- **THEN** it accepts workflow and worker connections on port 7233 while consuming less than 100 MB of system RAM

### Requirement: Production-ready Reverse Proxy and HTTPS
The deployment SHALL provide a Caddy or Nginx configuration that terminates TLS, serves the Next.js frontend, proxies `/runs` and API endpoints, and supports SSE trace streaming without buffering.

#### Scenario: Live trace streaming through reverse proxy
- **WHEN** a client connects to the `/runs/{id}/events` SSE endpoint
- **THEN** progress trace events are streamed in real time without buffering or premature connection drops
