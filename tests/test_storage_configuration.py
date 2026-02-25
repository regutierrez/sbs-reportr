from pathlib import Path

from reportr.app.web_api import (
    DATA_ROOT_ENV,
    REPORTS_ROOT_ENV,
    SESSIONS_ROOT_ENV,
    create_app,
    _resolve_repository_roots,
)
from reportr.storage import FileSystemReportRepository


def test_resolve_repository_roots_defaults_to_repo_data(monkeypatch) -> None:
    monkeypatch.delenv(DATA_ROOT_ENV, raising=False)
    monkeypatch.delenv(SESSIONS_ROOT_ENV, raising=False)
    monkeypatch.delenv(REPORTS_ROOT_ENV, raising=False)

    sessions_root, reports_root = _resolve_repository_roots()

    repo_root = Path(__file__).resolve().parents[1]
    assert sessions_root == repo_root / "data" / "sessions"
    assert reports_root == repo_root / "data" / "reports"


def test_resolve_repository_roots_uses_data_root_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(DATA_ROOT_ENV, (tmp_path / "runtime-data").as_posix())
    monkeypatch.delenv(SESSIONS_ROOT_ENV, raising=False)
    monkeypatch.delenv(REPORTS_ROOT_ENV, raising=False)

    sessions_root, reports_root = _resolve_repository_roots()

    assert sessions_root == tmp_path / "runtime-data" / "sessions"
    assert reports_root == tmp_path / "runtime-data" / "reports"


def test_resolve_repository_roots_prefers_explicit_session_and_report_roots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    sessions_root_override = tmp_path / "custom-sessions"
    reports_root_override = tmp_path / "custom-reports"

    monkeypatch.setenv(DATA_ROOT_ENV, (tmp_path / "runtime-data").as_posix())
    monkeypatch.setenv(SESSIONS_ROOT_ENV, sessions_root_override.as_posix())
    monkeypatch.setenv(REPORTS_ROOT_ENV, reports_root_override.as_posix())

    sessions_root, reports_root = _resolve_repository_roots()

    assert sessions_root == sessions_root_override
    assert reports_root == reports_root_override


def test_create_app_uses_configured_data_root(monkeypatch, tmp_path: Path) -> None:
    data_root = tmp_path / "service-data"

    monkeypatch.setenv(DATA_ROOT_ENV, data_root.as_posix())
    monkeypatch.delenv(SESSIONS_ROOT_ENV, raising=False)
    monkeypatch.delenv(REPORTS_ROOT_ENV, raising=False)

    app = create_app(session_ttl_seconds=0, cleanup_interval_seconds=0)
    repository = app.state.report_repository

    assert isinstance(repository, FileSystemReportRepository)
    assert repository.sessions_root == data_root / "sessions"
    assert repository.reports_root == data_root / "reports"
