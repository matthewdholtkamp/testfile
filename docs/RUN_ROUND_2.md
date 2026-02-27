# RUN ROUND 2 Workflow

`RUN ROUND 2` is the daily operational workflow for rebuilding needed Drive folders and uploading each day's XML corpus.

## Trigger modes

- Scheduled: once per day (UTC)
- Manual: Actions → **RUN ROUND 2** → **Run workflow**

## Required GitHub secrets

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `DRIVE_ROOT_FOLDER_ID`

## Manual inputs

- `day` (optional, `YYYY-MM-DD`; blank = today UTC)
- `reset_root` (`true` or `false`)

## What it does

1. Builds daily XML corpus into `data/xml_daily/<day>/`.
2. Rebuilds required Drive folders under root:
   - `INBOX`
   - `XML_DAILY`
   - `LOGS`
   - `ARCHIVE`
3. Uploads files into `XML_DAILY/<day>/`.
4. Cleans up temporary credentials file.
