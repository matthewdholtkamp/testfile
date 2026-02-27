from pathlib import Path

from tools.drive_flat_sync import resolve_credentials_path


def test_resolve_credentials_path_default(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    assert resolve_credentials_path() == Path("secrets/google_drive_service_account.json")


def test_resolve_credentials_path_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/key.json")
    assert resolve_credentials_path() == Path("/tmp/key.json")
