# uretOS

> uretOS is the operating system for modern manufacturing — connecting
> machines, processes and production data into one open, event-driven
> platform.

**Plan. Produce. Monitor. Optimize.**

uretOS is a Manufacturing Operating System, not a classical ERP: an open,
modular runtime for production. It connects machines, production processes,
and shopfloor data through event-driven communication and real-time
monitoring — with AI-assisted analysis and optimization planned for later
stages, from the shopfloor to the cloud.

## Architecture principles

- **Hyper-decoupled**: no shared runtime libraries between services.
  Duplication is preferred over coupling.
- **Message/event-driven**: all inter-service communication goes through
  RabbitMQ. No direct service-to-service calls.
- **CQRS per domain**: each domain with DB access gets a separate
  command-service (writes) and a generic, GraphQL-fed read-service (reads).
  Responses run over RPC.
- **Multi-tenant SaaS**: two user levels — `super_admin` (provisions tenants
  and connector boxes) and per-tenant users (`admin`, `operator`, ...).
  Each tenant gets its own isolated database containers.

## Status

Early rebuild (`v1`) of the project — the previous `uretos` repository is
kept as a proof-of-concept / reference, not as a base to build on.