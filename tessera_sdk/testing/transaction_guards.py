"""AST architecture guards for transaction ownership.

Each rule collects violations keyed by ``path::function::detail`` and compares
them with a JSON baseline of the violations that existed when the guards were
adopted. A violation missing from the baseline fails; so does a baseline entry
that no longer occurs, so every migration slice shrinks the baseline. A rule
is fully enforced once its baseline is empty.

In a service::

    # tests/architecture/test_transaction_boundaries.py
    from pathlib import Path

    import pytest

    from tessera_sdk.testing.transaction_guards import (
        RULE_NAMES,
        TransactionGuardConfig,
        assert_matches_baseline,
    )

    CONFIG = TransactionGuardConfig(
        app_root=Path(__file__).parents[2] / "app",
        baseline_path=Path(__file__).with_name("transaction_baseline.json"),
        early_commit_allowlist={
            ("tasks/send_task.py", "_send"): "lease claimed before provider call",
        },
    )

    @pytest.mark.parametrize("rule", RULE_NAMES)
    def test_transaction_rule_matches_baseline(rule):
        assert_matches_baseline(CONFIG, rule)

Regenerate the baseline after a migration slice with
``UPDATE_TRANSACTION_BASELINE=1 pytest tests/architecture``.
"""

from __future__ import annotations

import ast
import json
import os
import re
from collections import Counter
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path

UPDATE_ENV_VAR = "UPDATE_TRANSACTION_BASELINE"

DEFAULT_TRANSACTION_DIRS = (
    "repositories",
    "commands",
    "routers",
    "mcp",
    "events",
    "tasks",
    "cli",
    "services",
    "webhooks",
)
TRANSACTION_METHODS = frozenset({"commit", "rollback", "close", "begin"})
SESSION_FACTORY_NAMES = frozenset({"SessionLocal", "sessionmaker"})
SESSION_MANAGER_METHODS = frozenset({"create_session", "get_db", "db_session"})
DML_FUNCTIONS = frozenset({"update", "delete", "insert"})
# Receivers that are SQLAlchemy sessions by naming convention: db, self.db,
# session, self._db, db_session, ...
DEFAULT_SESSION_RECEIVER = re.compile(r"(^|\.)_?(db|session|db_session)$")


@dataclass(frozen=True)
class TransactionGuardConfig:
    """Where a service keeps its code and what it allows."""

    app_root: Path
    baseline_path: Path
    # Layers that must never end a transaction.
    transaction_dirs: tuple[str, ...] = DEFAULT_TRANSACTION_DIRS
    repository_dirs: tuple[str, ...] = ("repositories",)
    command_dirs: tuple[str, ...] = ("commands",)
    # Files (relative to app_root) allowed to construct sessions.
    session_modules: tuple[str, ...] = ("db.py",)
    # Files (relative to app_root) that implement the shared mutation helpers.
    repository_base_modules: tuple[str, ...] = ("repositories/base_repository.py",)
    # Names the DatabaseManager instance is bound to.
    manager_names: tuple[str, ...] = ("db_manager",)
    # Allowlisted early commits: (path relative to app_root, function) -> reason.
    early_commit_allowlist: Mapping[tuple[str, str], str] = field(default_factory=dict)
    session_receiver: re.Pattern[str] = DEFAULT_SESSION_RECEIVER


def _parse(path: Path) -> tuple[ast.AST, dict[ast.AST, ast.AST]]:
    tree = ast.parse(path.read_text())
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    return tree, parents


def _enclosing_function(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    current = parents.get(node)
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current.name
        current = parents.get(current)
    return "<module>"


def _iter_files(
    config: TransactionGuardConfig, dirs: tuple[str, ...] | None
) -> Iterator[Path]:
    if dirs is None:
        yield from sorted(config.app_root.rglob("*.py"))
        return
    for directory in dirs:
        root = config.app_root / directory
        if root.exists():
            yield from sorted(root.rglob("*.py"))


def _relative(config: TransactionGuardConfig, path: Path) -> str:
    return path.relative_to(config.app_root).as_posix()


def _chain_contains_call(node: ast.AST, name: str) -> bool:
    """True if a chain like ``self.db.query(X).filter(...)`` calls ``.name()``."""
    while True:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == name:
                return True
            node = func
        elif isinstance(node, ast.Attribute):
            node = node.value
        else:
            return False


def _root_call_name(node: ast.AST) -> str | None:
    """``update(X).where(...).values(...)`` -> ``"update"``."""
    while True:
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            node = node.func
        elif isinstance(node, ast.Attribute):
            node = node.value
        else:
            return None


def transaction_lifecycle_violations(config: TransactionGuardConfig) -> list[str]:
    """Session commit/rollback/close/begin outside the execution boundary."""
    violations = []
    for path in _iter_files(config, config.transaction_dirs):
        tree, parents = _parse(path)
        relative = _relative(config, path)
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in TRANSACTION_METHODS
            ):
                continue
            if not config.session_receiver.search(ast.unparse(node.func.value)):
                continue
            method = node.func.attr
            function = _enclosing_function(node, parents)
            if (
                method == "commit"
                and (relative, function) in config.early_commit_allowlist
            ):
                continue
            violations.append(f"{relative}::{function}::{method}")
    return violations


def session_construction_violations(config: TransactionGuardConfig) -> list[str]:
    """Sessions created, or the manager passed around, outside session modules."""
    allowed = {config.app_root / module for module in config.session_modules}
    manager_names = set(config.manager_names)
    violations = []
    for path in _iter_files(config, None):
        if path in allowed:
            continue
        tree, parents = _parse(path)
        relative = _relative(config, path)
        for node in ast.walk(tree):
            function = _enclosing_function(node, parents)
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in SESSION_FACTORY_NAMES:
                    violations.append(f"{relative}::{function}::{func.id}")
                elif (
                    isinstance(func, ast.Attribute)
                    and func.attr in SESSION_MANAGER_METHODS
                    and ast.unparse(func.value).split(".")[-1] in manager_names
                ):
                    manager = ast.unparse(func.value).split(".")[-1]
                    violations.append(f"{relative}::{function}::{manager}.{func.attr}")
            # Passing the manager or its methods around (e.g. to a service
            # factory) hands session ownership to someone else.
            elif (
                isinstance(node, ast.Name)
                and node.id in manager_names
                and not isinstance(parents.get(node), ast.Attribute)
            ):
                violations.append(f"{relative}::{function}::{node.id}")
            elif (
                isinstance(node, ast.Attribute)
                and node.attr in SESSION_MANAGER_METHODS
                and ast.unparse(node.value).split(".")[-1] in manager_names
                and not (
                    isinstance(parents.get(node), ast.Call)
                    and parents[node].func is node
                )
            ):
                manager = ast.unparse(node.value).split(".")[-1]
                violations.append(f"{relative}::{function}::{manager}.{node.attr}")
    return violations


def bare_exception_violations(config: TransactionGuardConfig) -> list[str]:
    """``raise Exception(...)`` in commands (the rollback-and-rewrap pattern)."""
    violations = []
    for path in _iter_files(config, config.command_dirs):
        tree, parents = _parse(path)
        relative = _relative(config, path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or node.exc is None:
                continue
            exc = node.exc
            target = exc.func if isinstance(exc, ast.Call) else exc
            if isinstance(target, ast.Name) and target.id == "Exception":
                function = _enclosing_function(node, parents)
                violations.append(f"{relative}::{function}::raise Exception")
    return violations


def identity_map_violations(config: TransactionGuardConfig) -> list[str]:
    """``expire_all()`` or ``synchronize_session=False`` anywhere."""
    violations = []
    for path in _iter_files(config, None):
        tree, parents = _parse(path)
        relative = _relative(config, path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = _enclosing_function(node, parents)
            if isinstance(node.func, ast.Attribute) and node.func.attr == "expire_all":
                violations.append(f"{relative}::{function}::expire_all")
            for keyword in node.keywords:
                if (
                    keyword.arg == "synchronize_session"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is False
                ):
                    violations.append(
                        f"{relative}::{function}::synchronize_session=False"
                    )
                if keyword.arg == "execution_options" and isinstance(
                    keyword.value, ast.Dict
                ):
                    for key, value in zip(
                        keyword.value.keys, keyword.value.values, strict=True
                    ):
                        if (
                            isinstance(key, ast.Constant)
                            and key.value == "synchronize_session"
                            and isinstance(value, ast.Constant)
                            and value.value is False
                        ):
                            violations.append(
                                f"{relative}::{function}::synchronize_session=False"
                            )
    return violations


def unsynchronized_dml_violations(config: TransactionGuardConfig) -> list[str]:
    """Set-based DML in repositories that bypasses ``Repository``'s helpers."""
    base_modules = {
        config.app_root / module for module in config.repository_base_modules
    }
    violations = []
    for path in _iter_files(config, config.repository_dirs):
        if path in base_modules:
            continue
        tree, parents = _parse(path)
        relative = _relative(config, path)
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            ):
                continue
            attr = node.func.attr
            receiver = node.func.value
            detail = None
            # Legacy Query DML: self.db.query(X).filter(...).update()/delete()
            if attr in {"update", "delete"} and _chain_contains_call(receiver, "query"):
                detail = f"query.{attr}"
            # 2.0-style DML executed directly on the session.
            elif (
                attr in {"execute", "scalar", "scalars"}
                and config.session_receiver.search(ast.unparse(receiver))
                and node.args
                and _root_call_name(node.args[0]) in DML_FUNCTIONS
            ):
                detail = f"session.{attr}({_root_call_name(node.args[0])})"
            if detail:
                function = _enclosing_function(node, parents)
                violations.append(f"{relative}::{function}::{detail}")
    return violations


RULES: dict[str, Callable[[TransactionGuardConfig], list[str]]] = {
    "transaction_lifecycle": transaction_lifecycle_violations,
    "session_construction": session_construction_violations,
    "bare_exception_in_commands": bare_exception_violations,
    "identity_map": identity_map_violations,
    "unsynchronized_dml": unsynchronized_dml_violations,
}
RULE_NAMES = sorted(RULES)


def load_baseline(config: TransactionGuardConfig) -> dict[str, dict[str, int]]:
    if not config.baseline_path.exists():
        return {}
    return json.loads(config.baseline_path.read_text())


def write_baseline(config: TransactionGuardConfig) -> None:
    baseline = {
        rule: dict(sorted(Counter(collect(config)).items()))
        for rule, collect in RULES.items()
    }
    config.baseline_path.write_text(json.dumps(baseline, indent=2) + "\n")


def compare_with_baseline(
    config: TransactionGuardConfig, rule: str
) -> tuple[list[str], list[str]]:
    """Return ``(new, fixed)``: violations not in the baseline, and baseline
    entries that no longer occur."""
    actual = Counter(RULES[rule](config))
    allowed = Counter(load_baseline(config).get(rule, {}))
    new = sorted((actual - allowed).elements())
    fixed = sorted((allowed - actual).elements())
    return new, fixed


def assert_matches_baseline(config: TransactionGuardConfig, rule: str) -> None:
    """Fail on new violations and on stale baseline entries.

    With ``UPDATE_TRANSACTION_BASELINE=1`` the baseline is rewritten first.
    """
    if os.environ.get(UPDATE_ENV_VAR) == "1":
        write_baseline(config)

    new, fixed = compare_with_baseline(config, rule)
    assert not new, f"New {rule} violations:\n  " + "\n  ".join(new)
    assert not fixed, (
        f"{rule} violations were removed but are still in the baseline; "
        f"regenerate it with {UPDATE_ENV_VAR}=1:\n  " + "\n  ".join(fixed)
    )
