from pathlib import Path

from tools.drive_flat_sync import (
    ROUND2_FOLDERS,
    resolve_credentials_path,
    resolve_drive_root_id,
    should_rebuild_folders,
)


def test_resolve_credentials_path_default(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    assert resolve_credentials_path() == Path("secrets/google_drive_service_account.json")


def test_resolve_credentials_path_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/key.json")
    assert resolve_credentials_path() == Path("/tmp/key.json")


def test_round2_folder_contract():
    assert ROUND2_FOLDERS == ["INBOX", "XML_DAILY", "LOGS", "ARCHIVE"]


def test_should_rebuild_folders_from_env(monkeypatch):
    monkeypatch.setenv("ROUND2_REBUILD_FOLDERS", "1")
    assert should_rebuild_folders(False) is True


def test_should_rebuild_folders_from_cli(monkeypatch):
    monkeypatch.delenv("ROUND2_REBUILD_FOLDERS", raising=False)
    assert should_rebuild_folders(True) is True


def test_resolve_drive_root_id_legacy_first(monkeypatch):
    monkeypatch.setenv("DRIVE_FOLDER_ID", "legacy")
    monkeypatch.setenv("DRIVE_ROOT_FOLDER_ID", "new")
    assert resolve_drive_root_id() == "legacy"


def test_resolve_drive_root_id_new_fallback(monkeypatch):
    monkeypatch.delenv("DRIVE_FOLDER_ID", raising=False)
    monkeypatch.setenv("DRIVE_ROOT_FOLDER_ID", "new")
    assert resolve_drive_root_id() == "new"
