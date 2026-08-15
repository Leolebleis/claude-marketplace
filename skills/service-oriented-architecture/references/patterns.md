# Worked Patterns

Full-mode reference implementations for one domain (`bookmarks`). Each section shows the correct form; BAD blocks show the specific violation to avoid.

## Contents

- Entity with transitions
- Outcome types and the service
- Persistence adapter (DAO protocol + implementation)
- External client (facade protocol + implementation)
- Router
- API models and the divergence trigger
- Dependency wiring
- Import contracts (import-linter template)
- Tests with fakes

## Entity with transitions

```python
# src/bookmarks/model/bookmark.py
from dataclasses import dataclass, replace
from datetime import datetime


@dataclass(frozen=True)
class AlreadyArchived:
    bookmark_id: str


@dataclass(frozen=True)
class Bookmark:
    id: str
    url: str
    title: str
    tags: tuple[str, ...]
    archived: bool
    created_at: datetime

    def archive(self) -> "Bookmark | AlreadyArchived":
        # The invariant lives here, not in the service.
        if self.archived:
            return AlreadyArchived(bookmark_id=self.id)
        return replace(self, archived=True)
```

BAD — invariant checked in the service, entity rebuilt by hand:

```python
# service.py
if bookmark.archived:                      # entity's rule, wrong layer
    return ...
updated = Bookmark(id=bookmark.id, url=bookmark.url, ..., archived=True)  # by-hand rebuild
```

## Outcome types and the service

```python
# src/bookmarks/model/bookmark.py (continued)
@dataclass(frozen=True)
class ArchiveSucceeded:
    bookmark: Bookmark


@dataclass(frozen=True)
class BookmarkNotFound:
    bookmark_id: str


@dataclass(frozen=True)
class SyncRejected:
    detail: str


ArchiveResult = ArchiveSucceeded | AlreadyArchived | BookmarkNotFound | SyncRejected
```

```python
# src/bookmarks/service.py
class BookmarkService:
    def __init__(self, dao: BookmarkDAO, linkvault: LinkVaultFacade) -> None:
        self._dao = dao
        self._linkvault = linkvault

    async def archive_bookmark(self, bookmark_id: str) -> ArchiveResult:
        bookmark = await self._dao.get_by_id(bookmark_id)
        if bookmark is None:
            return BookmarkNotFound(bookmark_id=bookmark_id)

        match bookmark.archive():
            case AlreadyArchived() as already:
                return already
            case Bookmark() as archived:
                try:
                    await self._linkvault.notify_archived(archived)
                except LinkVaultError as exc:   # adapter raises, service translates
                    return SyncRejected(detail=str(exc))
                await self._dao.save(archived)
                return ArchiveSucceeded(bookmark=archived)

    async def create_bookmark(self, url: str, title: str, tags: tuple[str, ...]) -> Bookmark:
        # Single expected outcome: return the entity. No union, no SUCCESS wrapper.
        # Plain arguments — the service never sees API request models.
        bookmark = Bookmark(id=str(uuid.uuid4()), url=url, title=title,
                            tags=tags, archived=False, created_at=datetime.now(UTC))
        await self._dao.create(bookmark)
        return bookmark
```

BAD — the optional grab-bag result:

```python
@dataclass
class ArchiveResult:
    outcome: ArchiveOutcome          # enum
    bookmark: Bookmark | None = None # only valid on success
    error: str | None = None         # only valid on failure -> invalid states constructible
```

## Persistence adapter

```python
# src/bookmarks/dao.py  (domain level — defines what the domain needs)
class BookmarkDAO(Protocol):
    async def get_by_id(self, bookmark_id: str) -> Bookmark | None: ...
    async def create(self, bookmark: Bookmark) -> None: ...
    async def save(self, bookmark: Bookmark) -> None: ...
```

```python
# src/bookmarks/persistence/bookmark_db.py
class BookmarkDB(BookmarkDAO):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, bookmark_id: str) -> Bookmark | None:
        row = await self._session.get(BookmarkRow, bookmark_id)
        return self._to_entity(row) if row else None

    def _to_entity(self, row: BookmarkRow) -> Bookmark:
        # Mapping stays internal to the adapter.
        return Bookmark(id=row.id, url=row.url, title=row.title,
                        tags=tuple(row.tags), archived=row.archived,
                        created_at=row.created_at)
```

BAD — the row escapes:

```python
async def get_by_id(self, bookmark_id: str) -> BookmarkRow:   # ORM type in a domain signature
    return await self._session.get(BookmarkRow, bookmark_id)
```

## External client

```python
# src/bookmarks/facade.py  (domain level)
class LinkVaultError(Exception):
    """Raised by the adapter; the service translates it to an outcome."""

class LinkVaultFacade(Protocol):
    async def notify_archived(self, bookmark: Bookmark) -> None: ...
```

```python
# src/bookmarks/client/linkvault_client.py
class LinkVaultClient(LinkVaultFacade):
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def notify_archived(self, bookmark: Bookmark) -> None:
        payload = {"external_id": bookmark.id, "archived_url": bookmark.url}
        try:
            response = await self._http.post("/v1/archived", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LinkVaultError(f"LinkVault sync failed: {exc}") from exc
```

BAD — provider shape leaks into the service:

```python
# service.py
data = await self._client.post_raw("/v1/archived", ...)
if data["status"]["code"] != "OK":        # provider JSON read outside the adapter
    ...
```

## Router

```python
# src/bookmarks/router.py
@router.post("/{bookmark_id}/archive")
async def archive_bookmark(
    bookmark_id: str,
    service: BookmarkService = Depends(get_bookmark_service),
) -> BookmarkAPIResponse:
    result = await service.archive_bookmark(bookmark_id)
    match result:
        case ArchiveSucceeded(bookmark=b):
            return BookmarkAPIResponse.from_entity(b)
        case AlreadyArchived(bookmark_id=bid):
            raise HTTPException(status_code=409, detail=f"{bid} already archived")
        case BookmarkNotFound():
            raise HTTPException(status_code=404)
        case SyncRejected():
            raise HTTPException(status_code=503, detail="archive not applied")
        case _:
            assert_never(result)
```

One case per outcome, `assert_never` closing the match. The router decides HTTP semantics (here: already-archived maps to 409; a team could equally choose 200-idempotent — that decision lives in the router, nowhere else).

## API models and the divergence trigger

```python
# src/bookmarks/model/api/responses.py
class BookmarkAPIResponse(BaseModel):
    id: str
    url: str
    title: str
    tags: list[str]          # diverged: tuple in domain, list on the wire
    archived: bool

    @classmethod
    def from_entity(cls, bookmark: Bookmark) -> "BookmarkAPIResponse":
        return cls(id=bookmark.id, url=bookmark.url, title=bookmark.title,
                   tags=list(bookmark.tags), archived=bookmark.archived)
```

While shapes are field-for-field identical, `from_entity` (or direct construction in the router) is enough — no `mapper.py`. Once the divergence trigger in SKILL.md fires (here: `tags` is a tuple in the domain, a list on the wire, so `from_entity` carries it), grow into `mapper.py` when the mapping is shared across handlers.

## Dependency wiring

```python
# src/bookmarks/dependencies.py
def get_bookmark_service(
    session: AsyncSession = Depends(get_session),
    http: httpx.AsyncClient = Depends(get_linkvault_http),
) -> BookmarkService:
    return BookmarkService(dao=BookmarkDB(session), linkvault=LinkVaultClient(http))
```

## Import contracts (import-linter template)

One contract pair per domain folder, added at folder creation. Substitute the domain name for `bookmarks`; `include_external_packages` is required for the framework-free contract.

```ini
[importlinter]
root_package = src
include_external_packages = True

[importlinter:contract:bookmarks-onion]
name = bookmarks dependency rule
type = layers
layers =
    src.bookmarks.router
    src.bookmarks.persistence : src.bookmarks.client
    src.bookmarks.service

[importlinter:contract:bookmarks-pure-domain]
name = bookmarks domain is framework-free
type = forbidden
source_modules =
    src.bookmarks.service
    src.bookmarks.model.bookmark
    src.bookmarks.dao
    src.bookmarks.facade
forbidden_modules =
    fastapi
    sqlalchemy
    httpx
```

Run `lint-imports` after any structural change; a contract failure is a failing test.

## Tests with fakes

```python
# tests/bookmarks/test_service.py
class FakeBookmarkDAO(BookmarkDAO):
    def __init__(self) -> None:
        self._store: dict[str, Bookmark] = {}

    async def get_by_id(self, bookmark_id: str) -> Bookmark | None:
        return self._store.get(bookmark_id)

    async def create(self, bookmark: Bookmark) -> None:
        self._store[bookmark.id] = bookmark

    async def save(self, bookmark: Bookmark) -> None:
        self._store[bookmark.id] = bookmark


class FakeLinkVault(LinkVaultFacade):
    def __init__(self, failing: bool = False) -> None:
        self.failing = failing
        self.notified: list[str] = []

    async def notify_archived(self, bookmark: Bookmark) -> None:
        if self.failing:
            raise LinkVaultError("down")
        self.notified.append(bookmark.id)


async def test_archive_reports_sync_rejected_and_does_not_persist():
    dao, vault = FakeBookmarkDAO(), FakeLinkVault(failing=True)
    service = BookmarkService(dao=dao, linkvault=vault)
    await dao.create(make_bookmark(id="b1", archived=False))

    result = await service.archive_bookmark("b1")

    assert isinstance(result, SyncRejected)
    stored = await dao.get_by_id("b1")
    assert stored is not None and stored.archived is False   # state unchanged on failure
```

The service is fully exercisable with no database, no network, and no mock library — the protocols make the fakes trivial. If a service test needs more than fakes, an adapter has leaked inward.
