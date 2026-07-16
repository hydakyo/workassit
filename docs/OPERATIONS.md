# Project OS Operations Guide

## Data model and recovery

Each project remains a self-contained filesystem directory. `project.json` stores metadata, workflow, rollout and delivery records; attached documents remain in their routed project folders. The app keeps a `.bak` copy whenever it atomically rewrites JSON metadata.

Use **Backup Project** before a major rollout or metadata migration. Backups run in the background and are stored under `.projectos/backups/`. **Restore Backup** never overwrites an existing project: it extracts into a new `Restored_*` directory below the first configured workspace root.

If project creation or restore is interrupted, do not delete its `.projectos/staging/` directory or incomplete restored directory. Inspect its `operation.json`/contents, retain a copy, then either finish recovery manually or remove it after confirming it is not needed.

## Delivery readiness

A delivery package is created only when every task is `Done`, every required artifact is attached, and every attached artifact is `Approved`. The ZIP and each included artifact have SHA-256 checksums recorded in delivery/project metadata.

## Cloud AI

Cloud AI scrubs common secrets and network identifiers before requesting a provider. Review the selected provider, endpoint and model in Settings before submitting project context. Do not place credentials in project files or task descriptions.

## Diagnostics

Application logs are stored under `%APPDATA%\ProjectOS\logs`. They intentionally omit API keys and other credential values. For a corrupted project, preserve the project directory and `project.json.bak` before attempting manual repair.
