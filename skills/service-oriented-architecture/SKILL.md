---
name: service-oriented-architecture
description: "Use when building or extending a backend API or web service: creating a new service, adding endpoints, integrating an external API, adding persistence, or structuring a project. Also use on layer-coupling symptoms: ORM models or provider JSON leaking into business logic, framework HTTP errors (e.g. HTTPException) raised outside routers, circular imports between layers, or one model shared across router, service, and database."
---

# Service Oriented Architecture

Architectural guidance for building services. Python/FastAPI is the reference stack; rules are stated by category (web framework, ORM, HTTP client) so they translate to other stacks.

**Core principle:** Source code dependencies point only inward, toward higher-level policy. Nothing in an inner layer knows anything about an outer layer. Everything else here exists to enforce that rule or to stop it being over-applied.

**Not for:** one-off scripts, CLI tools, throwaway prototypes, or libraries.

## Pick the Mode First

Pick the mode per domain folder when creating it — deployment status is irrelevant to the choice.

**Lightweight mode** applies when ALL of these are true (observable facts, not judgment):

- Every operation is a direct create/read/update/delete/list over one table or resource
- There is no business rule beyond field validation — no if-statement about domain state
- The code calls no other service and no external API
- It has a single internal consumer (admin tool, internal dashboard)

**Full mode** applies otherwise.

Lightweight shape: the transport layer calls the persistence protocol directly and does its own HTTP error translation — no service class, no outcome types, no API mapper. In Python: `router.py` + `dao.py` (protocol) + `persistence/`. The DAO still returns plain domain objects, never ORM rows, and the folder still gets its import contracts (see Verify below) — both modes, no exceptions.

**Promotion is event-driven and per operation.** The first business-rule if-statement, the first external call, or a second consumer promotes that operation: add the service class and outcome type for it, and leave unpromoted operations calling the DAO from the router. Full-mode files appear as operations need them, not folder-wide.

## The Architecture Onion (full mode)

Three layers, strict dependency direction: **API -> Domain <- Infrastructure**. Deliberately three — the direction, not the count, is the rule.

| Layer | Contains | May import | Must never import |
|-------|----------|-----------|-------------------|
| Domain (`model/`, `service.py`, `dao.py`, `facade.py`) | Entities, services, outcome types, protocols | Other domain code, stdlib | The web framework (`fastapi`), ORM/DB driver (`sqlalchemy`), HTTP client (`httpx`), API request/response models, anything in `persistence/` or `client/` |
| Infrastructure (`persistence/`, `client/`) | Concrete DBs, HTTP clients, their DTOs and mapping | Domain entities and protocols, the ORM/HTTP libraries | The web framework, router code, API models |
| API (`router.py`, `model/api/`) | Routes, request/response models, HTTP translation | Domain services, entities, outcomes | ORM, HTTP client, `persistence/`, `client/` |

The domain defines the protocols (`dao.py`, `facade.py`); infrastructure implements them. If a protocol lives next to its implementation, the dependency arrow points outward — that is the violation, wherever the file sits.

## Folder Structure

Top-level folders are named by domain, not by technical concern — the tree should say what the service does (`bookmarks/`, `collections/`), not what framework it uses (`routers/`, `services/`).

```
src/
  bookmarks/                  # full mode
    router.py
    service.py
    mapper.py                 # API <-> domain (only once shapes diverge; see Mappers)
    dao.py                    # persistence protocol (domain-level)
    facade.py                 # external-service protocol (domain-level)
    dependencies.py
    model/
      bookmark.py             # domain entity + outcome types
      api/
        requests.py
        responses.py
    client/
      linkvault_client.py     # implements facade; maps provider payloads internally
    persistence/
      bookmark_db.py          # implements dao; maps rows internally
  flags/                      # lightweight mode: router.py, dao.py, persistence/
  config.py
  main.py
```

Each domain folder is a self-contained mini-service: extracting it means replacing direct calls with an HTTP interface, nothing more. Anything outside a domain folder is shared plumbing (config, DB connection, base classes). Wire dependencies with the framework's built-in mechanism — factory functions in `dependencies.py` (FastAPI: `Depends`); no DI-container libraries.

## Entities: Immutable, With Behavior

Entities are immutable and own their invariants and state transitions — in Python, frozen dataclasses. Transitions return new instances; never mutate, never let services rebuild entity state by hand.

```python
@dataclass(frozen=True)
class Bookmark:
    id: str
    url: str
    archived: bool

    def archive(self) -> "Bookmark | AlreadyArchived":
        if self.archived:
            return AlreadyArchived(bookmark_id=self.id)
        return replace(self, archived=True)
```

If a service contains `replace(entity, ...)` or reconstructs an entity field-by-field to change its state, that logic belongs on the entity.

## Services and Typed Outcomes

Services orchestrate use cases across entities and protocols.

**Expected domain outcomes are returned as values; unexpected failures raise.** An outcome type is a union of frozen dataclasses — one per case, each named as a domain statement of what happened, each carrying only the data valid for that case:

```python
@dataclass(frozen=True)
class ArchiveSucceeded:
    bookmark: Bookmark

@dataclass(frozen=True)
class BookmarkNotFound:
    bookmark_id: str

@dataclass(frozen=True)
class SyncRejected:          # upstream sync system refused or was unreachable
    detail: str

ArchiveResult = ArchiveSucceeded | AlreadyArchived | BookmarkNotFound | SyncRejected
```

Rules that make this pattern earn its cost:

- **Only where at least two expected outcomes exist.** A single-case `SUCCESS` union is ceremony: return the entity directly and let unexpected errors raise.
- **Names are domain statements** (`BookmarkNotFound`, `InsufficientFunds`), never generic (`ERROR`, `FAILED`, `INVALID`). The union is a reviewable, in-words statement of every case the code plans for — write it before implementing.
- **No optional grab-bag fields.** `entity: X | None` + `error: str | None` on one class makes invalid states representable; the union makes them unconstructible.
- **Exhaustiveness is enforced, not hoped for.** Every `match` ends with `case _: assert_never(result)` (`typing.assert_never`), so adding a case breaks the type check instead of silently returning `None`.
- **Adapters raise, services translate.** Infrastructure (clients, DBs) raises its own exception types; the service catches those it expects and returns the corresponding outcome. Exceptions that reach the top are bugs or infra failures — let them surface.

## Mappers: Mandatory at Infrastructure, On-Divergence at the API

Two tiers, because the boundaries differ:

- **Infrastructure boundaries (persistence, clients): mapping is mandatory.** No ORM row, provider payload, or raw dict crosses into the domain — the adapter accepts and returns domain entities only. Start with private `_to_entity`/`_to_dto` methods on the adapter; promote to a `*Mapper` class when the mapping is shared or outgrows a screenful. The mapping is internal to the adapter; services never see it.
- **API boundary: introduce `mapper.py` the moment any field differs** between the API model and the domain entity in name, type, optionality, or shape — or when a request needs assembly beyond field copying. Until then, construct the response model directly from the entity in the router. Divergence is the trigger; do not pre-build identity mappers, and do not "simplify" an existing mapper away once shapes have diverged.

Either way: typed models cross boundaries, never dicts. A dict is an implicit contract nobody can check.

## Routers

Thin: parse, delegate to one service call, translate the outcome to HTTP. Target under ~15 executable lines per handler. HTTP status decisions — framework HTTP errors and status codes (FastAPI: `HTTPException`) — exist only here (and in lightweight-mode routers). If a handler grows past that, logic has leaked in — move it to the service.

```python
match result:
    case ArchiveSucceeded(bookmark=b):
        return BookmarkAPIResponse.from_entity(b)
    case AlreadyArchived():
        raise HTTPException(status_code=409)
    case BookmarkNotFound():
        raise HTTPException(status_code=404)
    case SyncRejected():
        raise HTTPException(status_code=503)
    case _:
        assert_never(result)
```

## Between Services

- **One database, one service.** No other service touches it — schema coupling through a shared database is invisible and unbreakable. Share data through the owning service's API.
- **No shared domain models.** Two services that both handle a `Condition` model own separate models and map at the API boundary, even if identical today — they change for different reasons.
- **Compatibility lives in contract tests**, not in a shared library.

When unsure how to split components or domains, arbitrate with the component cohesion and coupling principles (REP, CCP, CRP, ADP, SDP, SAP).

## Verify the Boundaries Mechanically

Prose rules drift; import contracts don't. Enforce the dependency rule with an import-boundary linter for the language, and treat a contract failure like a failing test. Python reference: [import-linter](https://pypi.org/project/import-linter/) — add one layers contract plus one framework-free contract per domain folder at folder creation (template in [references/patterns.md](references/patterns.md)), and run `lint-imports` after any structural change.

## Red Flags — Stop and Re-check

| Rationalization | Reality |
|----------------|---------|
| "The models are identical, share one" | Identical *today*. Layers change for different reasons; at infra boundaries, map anyway. |
| "It's a deployed service, so full ceremony applies" | Mode is chosen by the lightweight predicates, not by deployment status. Check them first. |
| "It's just CRUD, but I'll add the service layer to be safe" | A passthrough service is dead weight and hides the day it stops being CRUD. Lightweight mode, promote on the first rule. |
| "One SUCCESS outcome keeps it consistent" | A single-case union states nothing. Return the entity; consistency is not ceremony. |
| "Raise the HTTP error here, it's one line" | HTTP belongs to the router. The service reports what happened; the router decides what that means on the wire. |
| "We'll clean it up later" | Later never has more budget than now. The seams already exist — use them. |
| "Deadline, so skip the tests" | Tests are part of done in both modes. A lightweight-mode test is ten lines with a fake DAO. |

## Troubleshooting

- **Circular import between service and persistence** — the protocol is missing or lives next to its implementation. Move it to domain level (`dao.py`); persistence imports the protocol, never the reverse.
- **Service tests need a running database** — a concrete adapter leaked into the service. Inject the protocol; test with an in-memory fake.
- **A new `match` case silently returns `None`** — missing `assert_never`. Add the `case _` arm and run the type checker.
- **Adding one field touched five files** — if the operation is lightweight-eligible, you're in the wrong mode. If it's genuinely full-mode, that cost is the isolation working; check only whether the API tier actually diverged before keeping its mapper.
- **Provider JSON shape appears in service code** (`result["data"]["nested"]`) — the client is leaking. It must return domain entities; mapping is internal to the adapter (BAD example in [references/patterns.md](references/patterns.md)).

## Testing

Tests mirror `src/` by domain. Service tests are unit tests with in-memory fakes implementing the protocols — no DB, no network, no mocks of concrete classes. Router tests hit endpoints through the app with fakes wired via dependency overrides. Adapter tests mock at the transport level. Worked examples, including a full fake-DAO test: [references/patterns.md](references/patterns.md).
