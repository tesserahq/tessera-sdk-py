import json
import textwrap

import pytest

from tessera_sdk.testing.transaction_guards import (
    RULE_NAMES,
    RULES,
    TransactionGuardConfig,
    assert_matches_baseline,
    compare_with_baseline,
    write_baseline,
)


def _write(root, relative, source):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source))


@pytest.fixture
def app_root(tmp_path):
    root = tmp_path / "app"
    _write(
        root,
        "db.py",
        """
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker()
        db_manager = object()
        def get_db():
            with db_manager.db_session() as db:
                yield db
        """,
    )
    _write(
        root,
        "repositories/pet_repository.py",
        """
        class PetRepository:
            def create_pet(self, pet):
                self.db.add(pet)
                self.db.commit()

            def archive(self):
                self.db.query(Pet).filter(Pet.old).update({"archived": True})

            def purge(self):
                self.db.execute(delete(Pet))

            def listing(self):
                return self.db.execute(select(Pet)).all()

            def stale(self):
                self.db.query(Pet).update({"x": 1}, synchronize_session=False)
        """,
    )
    _write(
        root,
        "repositories/base_repository.py",
        """
        class Repository:
            def _execute_mutation(self, statement):
                return self.db.execute(update(Thing))
        """,
    )
    _write(
        root,
        "commands/create_pet_command.py",
        """
        class CreatePetCommand:
            def execute(self, data):
                try:
                    self.repo.create_pet(data)
                except Exception as e:
                    self.db.rollback()
                    raise Exception(f"Failed: {e}")
                client.close()
        """,
    )
    _write(
        root,
        "tasks/send_task.py",
        """
        def _send(db):
            db.commit()
        """,
    )
    _write(
        root,
        "main.py",
        """
        from app.db import db_manager
        factory = create_service_factory(OnboardCommand, db_manager)
        session = SessionLocal()
        """,
    )
    return root


def _config(app_root, **overrides):
    return TransactionGuardConfig(
        app_root=app_root,
        baseline_path=app_root.parent / "baseline.json",
        **overrides,
    )


def test_transaction_lifecycle_flags_session_calls_only(app_root):
    violations = RULES["transaction_lifecycle"](_config(app_root))

    assert sorted(violations) == [
        "commands/create_pet_command.py::execute::rollback",
        "repositories/pet_repository.py::create_pet::commit",
        "tasks/send_task.py::_send::commit",
    ]


def test_early_commit_allowlist_is_respected(app_root):
    config = _config(
        app_root,
        early_commit_allowlist={("tasks/send_task.py", "_send"): "lease claimed"},
    )

    assert "tasks/send_task.py::_send::commit" not in RULES["transaction_lifecycle"](
        config
    )


def test_session_construction_outside_the_session_module(app_root):
    violations = RULES["session_construction"](_config(app_root))

    assert sorted(violations) == [
        "main.py::<module>::SessionLocal",
        "main.py::<module>::db_manager",
    ]


def test_bare_exceptions_in_commands(app_root):
    assert RULES["bare_exception_in_commands"](_config(app_root)) == [
        "commands/create_pet_command.py::execute::raise Exception"
    ]


def test_identity_map_misuse(app_root):
    assert RULES["identity_map"](_config(app_root)) == [
        "repositories/pet_repository.py::stale::synchronize_session=False"
    ]


def test_unsynchronized_dml_skips_reads_and_the_base_module(app_root):
    violations = RULES["unsynchronized_dml"](_config(app_root))

    assert sorted(violations) == [
        "repositories/pet_repository.py::archive::query.update",
        "repositories/pet_repository.py::purge::session.execute(delete)",
        "repositories/pet_repository.py::stale::query.update",
    ]


def test_baseline_reports_new_and_fixed_violations(app_root):
    config = _config(app_root)
    write_baseline(config)
    baseline = json.loads(config.baseline_path.read_text())
    assert set(baseline) == set(RULE_NAMES)

    for rule in RULE_NAMES:
        assert compare_with_baseline(config, rule) == ([], [])

    # Fix one violation and add another.
    _write(
        app_root,
        "tasks/send_task.py",
        """
        def _send(db):
            pass

        def _other(session):
            session.rollback()
        """,
    )

    assert compare_with_baseline(config, "transaction_lifecycle") == (
        ["tasks/send_task.py::_other::rollback"],
        ["tasks/send_task.py::_send::commit"],
    )
    with pytest.raises(AssertionError, match="New transaction_lifecycle"):
        assert_matches_baseline(config, "transaction_lifecycle")


def test_update_env_var_rewrites_the_baseline(app_root, monkeypatch):
    config = _config(app_root)
    monkeypatch.setenv("UPDATE_TRANSACTION_BASELINE", "1")

    assert_matches_baseline(config, "transaction_lifecycle")

    assert config.baseline_path.exists()
