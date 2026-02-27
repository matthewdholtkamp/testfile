#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]
ROUND2_FOLDERS = ["INBOX", "XML_DAILY", "LOGS", "ARCHIVE"]


def resolve_credentials_path() -> Path:
    return Path(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "secrets/google_drive_service_account.json"))


def get_service():
    creds_path = resolve_credentials_path()
    if not creds_path.exists():
        raise RuntimeError(
            "Google credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS or place key at secrets/google_drive_service_account.json"
        )
    creds = service_account.Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def list_children(service, folder_id: str):
    query = f"'{folder_id}' in parents and trashed=false"
    resp = service.files().list(q=query, fields="files(id,name,mimeType)", pageSize=1000).execute()
    return resp.get("files", [])


def delete_tree(service, file_id: str):
    children = list_children(service, file_id)
    for child in children:
        if child["mimeType"] == "application/vnd.google-apps.folder":
            delete_tree(service, child["id"])
        service.files().delete(fileId=child["id"]).execute()


def ensure_folder(service, parent_id: str, name: str) -> str:
    query = (
        "mimeType='application/vnd.google-apps.folder' "
        f"and name='{name}' and '{parent_id}' in parents and trashed=false"
    )
    found = service.files().list(q=query, fields="files(id)", pageSize=1).execute().get("files", [])
    if found:
        return found[0]["id"]
    body = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    return service.files().create(body=body, fields="id").execute()["id"]


def ensure_round2_structure(service, root_id: str) -> dict[str, str]:
    folder_ids: dict[str, str] = {}
    for folder in ROUND2_FOLDERS:
        folder_ids[folder] = ensure_folder(service, root_id, folder)
    return folder_ids


def upload_flat(service, parent_id: str, local_day: Path):
    for path in sorted(local_day.iterdir()):
        if not path.is_file():
            continue
        media = MediaFileUpload(str(path), resumable=False)
        body = {"name": path.name, "parents": [parent_id]}
        service.files().create(body=body, media_body=media, fields="id").execute()


def main():
    parser = argparse.ArgumentParser(description="Flat Google Drive daily sync with optional root reset.")
    parser.add_argument("--local-day", required=True, help="Local folder for one day of XML corpus")
    parser.add_argument("--reset-root", action="store_true", help="Delete all children under DRIVE_ROOT_FOLDER_ID")
    parser.add_argument(
        "--rebuild-folders",
        action="store_true",
        help="Ensure ROUND 2 folder structure (INBOX/XML_DAILY/LOGS/ARCHIVE) under root before upload",
    )
    args = parser.parse_args()

    root_id = os.environ.get("DRIVE_ROOT_FOLDER_ID")
    if not root_id:
        raise RuntimeError("DRIVE_ROOT_FOLDER_ID is required")

    local_day = Path(args.local_day)
    if not local_day.exists() or not local_day.is_dir():
        raise RuntimeError(f"Local day folder not found: {local_day}")

    service = get_service()

    if args.reset_root:
        delete_tree(service, root_id)

    target_parent = root_id
    if args.rebuild_folders:
        structure = ensure_round2_structure(service, root_id)
        target_parent = structure["XML_DAILY"]

    day_folder_id = ensure_folder(service, target_parent, local_day.name)
    upload_flat(service, day_folder_id, local_day)
    print(f"Uploaded {local_day} to Drive folder {local_day.name}")


if __name__ == "__main__":
    main()
