# Managed database transactions

Every service built on this SDK follows one rule: **the entry point owns the
transaction.** An HTTP request, Celery task, tool call, CLI command, or event
handler opens one SQLAlchemy session. The session commits when the execution
succeeds, rolls back when an exception escapes, and closes. Repositories and
commands never call `commit()` or `rollback()`, so composing them stays atomic.

This is not a custom framework. SQLAlchemy's `Session` already implements the
Unit of Work pattern, and session-per-request is SQLAlchemy's documented web
pattern. This is the same model as Django's `ATOMIC_REQUESTS` plus
`transaction.on_commit()`. The SDK supplies the small amount of glue that
SQLAlchemy and FastAPI leave to the application. The pattern was piloted in
Sendly (tesserahq/sendly#135, #136) and Linden (mylinden-tech/linden-api#508).

## What the SDK provides

| Need | API |
|---|---|
| One session per non-HTTP execution | `db_manager.session_scope()` |
| One session per request, committed before the response is sent | `get_db, DbSession = create_db_dependency(db_manager)` (`tessera_sdk.server.dependencies`) |
| Side effects only after commit (events, task enqueues) | `on_commit(callback)` (`tessera_sdk.infra`) |
| Intentional partial success (skip a bad item in a batch) | `savepoint(session)` (`tessera_sdk.infra`) |
| Queries see changes staged earlier in the execution | `DatabaseManager(..., autoflush=True)` |
| Set-based UPDATE/DELETE that keeps loaded objects in sync | `Repository._execute_mutation` / `_scalar_mutation` (`tessera_sdk.infra`) |
| Auth/onboarding middlewares with managed sessions | `create_managed_user_service_factory(...)` (`tessera_sdk.server.user_service`) |
| Tests that behave like production | `execution_boundary`, `managed_db_override` (`tessera_sdk.testing`) |
| CI guards that keep transaction ownership at the boundary | `tessera_sdk.testing.transaction_guards` |

## Rules

- **Repositories** query, stage (`add`, attribute assignment, `delete`), and
  `flush()` only when they must return generated state: an id, a server
  default, or a lock or constraint result. `add()` + `flush()` + `refresh()`
  in a create method whose caller uses the new id is the common case. They
  never `commit()` or `rollback()`. With autoflush on, later queries in the
  same execution already see staged changes.
- **Commands** call repositories and let exceptions propagate unchanged. Do
  not use `try: ... except Exception: db.rollback(); raise Exception(...)`:
  it rolls back the caller's work too and destroys the exception type. If a
  low-level error needs translating, raise a typed domain exception with the
  original as `__cause__`.
- **Routes** declare `db: DbSession`. `DbSession` has no default value, so it
  goes before parameters that have defaults. For a non-2xx outcome, raise;
  never catch an error after staging writes and then return normally.
- **External calls** (HTTP APIs, email, object storage, brokers) never run
  inside an open transaction. Use one of these instead:
  - Call before the first write, when the result is an input.
  - `on_commit(...)`, for best-effort side effects.
  - An outbox row in the same transaction, for side effects that must happen
    eventually.
  - An early `session.commit()`, for a synchronous multi-phase workflow.
    Persist a pending state, commit, call the provider idempotently, then
    record the outcome. Early commits are allowed only in top-level workflows
    listed in the guard allowlist.
- **Events**: route the service's event gateway through `on_commit`, so
  events are dispatched only after commit and dropped on rollback.

## Adopting the pattern in a service

Migrate in this order. Each step is safe to deploy on its own.

1. **Session infrastructure** (`app/db.py`):

   ```python
   db_manager = DatabaseManager(..., autoflush=True)
   get_db, DbSession = create_db_dependency(db_manager)
   session_scope = db_manager.session_scope
   ```

   Replace every `db: Session = Depends(get_db)` with `db: DbSession`, in
   routes and in shared `get_*_by_id` dependencies. Remove any
   `app.db`-local copies of `on_commit`/`savepoint` and their `Session`
   listeners.
2. **Events**: make the event gateway's synchronous publish call
   `on_commit(lambda: dispatch(event))`.
3. **Other entry points**: Celery tasks, CLI commands, tool calls, and event
   destinations use `with session_scope() as db:`. The auth/onboarding
   middlewares receive `create_managed_user_service_factory(...)`. Delete any
   local session helpers and session middleware.
4. **Tests**:
   - Create the `db` fixture's sessionmaker with
     `join_transaction_mode="create_savepoint"` inside a rolled-back outer
     transaction.
   - Override `get_db` with `managed_db_override(db)`.
   - Run commands under `execution_boundary(db)` when a test asserts
     rollback.
   - Tests that only passed because a command's own `rollback()` discarded
     the whole test transaction should be marked `xfail(strict=True)` until
     their flow migrates.
5. **Guards**: add `tests/architecture/test_transaction_boundaries.py` (see
   the `transaction_guards` module docstring) and generate the baseline with
   `UPDATE_TRANSACTION_BASELINE=1`. The session-construction rule should
   reach zero after step 3.
6. **Repositories and commands**, one flow at a time:
   - Replace `commit()` with nothing, or with `flush()` where the method
     returns generated state.
   - Remove rollback-and-rewrap blocks.
   - Classify external calls.
   - Add a failure-injection test under `execution_boundary`.
   - Regenerate the baseline, which must shrink.

   Once every entry point commits at the end (steps 1–3), removing a
   repository commit is safe even for callers that have not migrated yet.

## Compatibility

- **`autoflush`**: `DatabaseManager` still defaults to `autoflush=False`, so
  a service that has not migrated does not change behavior when it upgrades
  the SDK. It will default to `True` once every service has adopted the
  pattern.
- **`create_service_factory`**: deprecated, because it hands the middlewares
  a session that nothing commits or rolls back.
- **Coexistence**: the SDK's commit listeners only run callbacks registered
  through `tessera_sdk.infra.on_commit`. A service can upgrade before
  removing its local copy without running any callback twice.
