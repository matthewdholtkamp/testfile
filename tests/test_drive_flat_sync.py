from pathlib import Path

from tools.drive_flat_sync import ROUND2_FOLDERS, resolve_credentials_path


def test_resolve_credentials_path_default(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    assert resolve_credentials_path() == Path("secrets/google_drive_service_account.json")


def test_resolve_credentials_path_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/key.json")
    assert resolve_credentials_path() == Path("/tmp/key.json")


def test_round2_folder_contract():
    assert ROUND2_FOLDERS == ["INBOX", "XML_DAILY", "LOGS", "ARCHIVE"]
