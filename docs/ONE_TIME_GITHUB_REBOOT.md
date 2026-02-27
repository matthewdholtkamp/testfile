# One-Time GitHub Drive Reboot Runbook

Use this when you want GitHub Actions to perform a single destructive Drive reset + re-upload.

## 1) Configure GitHub repository secrets

- `SERVICE_ACCOUNT_JSON` (legacy, preferred) or `GOOGLE_SERVICE_ACCOUNT_JSON` = full service-account JSON content
- `DRIVE_FOLDER_ID` (legacy, preferred) or `DRIVE_ROOT_FOLDER_ID` = target Google Drive folder ID

## 2) Run the workflow

1. Open **Actions** tab in GitHub.
2. Select **One-Time Drive Reboot**.
3. Click **Run workflow**.
4. Set:
   - `run_confirmation`: `RUN-DRIVE-REBOOT` (exact)
   - `day`: optional `YYYY-MM-DD` (blank = today UTC)
   - `reset_root`: `true` to wipe and restart, `false` to upload only

## 3) What it does

1. Builds XML corpus into `data/xml_daily/<day>/`.
2. Writes the service account key into `secrets/google_drive_service_account.json` during the run.
3. Optionally deletes all existing children under `DRIVE_FOLDER_ID` (legacy, preferred) or `DRIVE_ROOT_FOLDER_ID`.
4. Uploads all files from `data/xml_daily/<day>/` into a single Drive day folder.
5. Uploads the local day folder as a GitHub artifact.
6. Deletes the temporary service account key file.
7. Deletes this one-time workflow file from the branch after successful completion.

## Safety

The workflow will fail unless `run_confirmation` is exactly `RUN-DRIVE-REBOOT`.
