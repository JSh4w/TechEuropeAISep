## Purpose

Defines a lightweight, single-host runtime architecture capable of running Temporal, the API server, worker, and web frontend on an Ubuntu virtual machine under 1 GB total memory usage.

## ADDED Requirements

### Requirement: Lightweight Temporal Orchestration
The deployment SHALL utilize the standalone Temporal CLI development server (`temporal server start-dev` with embedded SQLite) rather than multi-container cluster images.

#### Scenario: Standalone Temporal execution
- **WHEN** the Temporal dev server is started with SQLite persistence, bound to `127.0.0.1`
- **THEN** it accepts workflow and worker connections on port 7233, and its resident memory is measured on the VM and recorded (target under 100 MB; the figure is to be verified, not assumed)

### Requirement: Hardened single-host baseline
The deployment SHALL expose only ports 80 and 443, bind Temporal and FastAPI to `127.0.0.1`, disable SSH password login, run services as a non-root user with `NoNewPrivileges` and `ProtectSystem`, apply rate limiting and security headers at the proxy, and keep headers, bodies and keys out of logs and traces.

#### Scenario: Internal ports not reachable
- **WHEN** a client outside the VM probes ports 7233, 8233 and 8000
- **THEN** the connections are refused

#### Scenario: Master secret handling
- **WHEN** the services start
- **THEN** the master secret is read from a root-owned `0600` environment file, and the key database is owned by the service user with mode `0600`

### Requirement: Production-ready Reverse Proxy and HTTPS
The deployment SHALL provide a Caddy or Nginx configuration that terminates TLS, serves the Next.js frontend, proxies `/runs` and API endpoints, and supports SSE trace streaming without buffering.

#### Scenario: Live trace streaming through reverse proxy
- **WHEN** a client connects to the `/runs/{id}/events` SSE endpoint
- **THEN** progress trace events are streamed in real time without buffering or premature connection drops
