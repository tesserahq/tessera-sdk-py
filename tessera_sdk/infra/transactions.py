"""
Transaction boundary helpers: one managed session per application execution.

SQLAlchemy's ``Session`` is the Unit of Work. An execution (HTTP request,
task, tool call, CLI command, event handler) opens one session through
``DatabaseManager.session_scope()``; it commits when the execution succeeds,
rolls back when an exception escapes, and closes. Repositories and commands
never end the transaction themselves.

This module adds the two pieces SQLAlchemy does not provide directly:

- ``on_commit(callback)``: run side effects (events, task enqueues) only after
  the enclosing transaction commits, and drop them if it rolls back. This is
  the equivalent of Django's ``transaction.on_commit``.
- ``savepoint(session)``: ``Session.begin_nested()`` that also discards the
  post-commit callbacks registered by the failed work.

Listeners are registered on the ``Session`` class once, when this module is
imported. Callbacks are stored under a key private to this module, so an
application that still carries its own copy of these listeners keeps running
only its own callbacks.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session, SessionTransaction

logger = logging.getLogger(__name__)

_ON_COMMIT_HOOKS = "tessera_on_commit_hooks"
_current_session: ContextVar[Session | None] = ContextVar(
    "tessera_current_session", default=None
)


def current_session() -> Session | None:
    """The session of the enclosing managed execution, if any."""
    return _current_session.get()


@contextmanager
def bind_session(session: Session | None) -> Iterator[Session | None]:
    """Make ``session`` the current session for the duration of the block.

    ``DatabaseManager.session_scope()`` does this for production code; tests
    use it to run code under a fixture session exactly as an entry point would.
    """
    token: Token = _current_session.set(session)
    try:
        yield session
    finally:
        _current_session.reset(token)


def on_commit(callback: Callable[[], Any], session: Session | None = None) -> None:
    """Run ``callback`` after the transaction commits.

    Inside a managed execution the callback is queued on the current (or
    given) session and runs after its next root commit; it is discarded if
    the transaction rolls back. Outside one it runs immediately.
    """
    active_session = session or _current_session.get()
    if active_session is None:
        callback()
        return

    hooks = active_session.info.setdefault(_ON_COMMIT_HOOKS, [])
    hooks.append(callback)


@contextmanager
def savepoint(session: Session) -> Iterator[None]:
    """Create a savepoint and discard callbacks registered by failed work.

    Use only where partial success is part of the contract (e.g. skipping an
    invalid item in a batch). The exception is re-raised; the outer
    transaction remains usable.
    """
    hooks = session.info.setdefault(_ON_COMMIT_HOOKS, [])
    mark = len(hooks)
    try:
        with session.begin_nested():
            yield
    except Exception:
        del hooks[mark:]
        raise


def _run_on_commit_hooks(session: Session) -> None:
    # Releasing a savepoint is not a durability boundary.
    if session.in_nested_transaction():
        return

    hooks = session.info.pop(_ON_COMMIT_HOOKS, [])
    if not hooks:
        return

    # Hooks run outside the committed execution: work they schedule must not
    # register itself on this session.
    with bind_session(None):
        for callback in hooks:
            try:
                callback()
            except Exception:
                logger.exception(
                    "Post-commit callback failed",
                    extra={
                        "callback": getattr(callback, "__qualname__", repr(callback))
                    },
                )


def _discard_on_root_rollback(
    session: Session, transaction: SessionTransaction
) -> None:
    if transaction.parent is None:
        session.info.pop(_ON_COMMIT_HOOKS, None)


def install_session_listeners() -> None:
    """Register the commit/rollback listeners on ``Session`` (idempotent)."""
    if not event.contains(Session, "after_commit", _run_on_commit_hooks):
        event.listen(Session, "after_commit", _run_on_commit_hooks)
    if not event.contains(Session, "after_soft_rollback", _discard_on_root_rollback):
        event.listen(Session, "after_soft_rollback", _discard_on_root_rollback)


install_session_listeners()
