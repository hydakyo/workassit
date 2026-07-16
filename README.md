# Project OS

Project OS is a Local-First desktop application for network and security deployment engineers.

## Features
- Local-first workspace discovery; project files remain directly accessible in File Explorer.
- Project scaffolding from templates, task workflow and required-artifact tracking.
- Routed artifact imports, version backup, audit history, undo and ZIP delivery packages.
- Atomic JSON project/settings writes plus a local SQLite search index.
- Cloud AI project review through OpenAI-compatible endpoints or Gemini, with sensitive-data redaction before requests leave the device.
- PyWebView desktop UI with multiple workspace roots and secure API-key storage in Windows Credential Manager.

## Setup
1. Ensure Python 3.11+ is installed.
2. Install dependencies: `pip install -r requirements.txt`
3. For development, install dev dependencies: `pip install -r requirements-dev.txt`

## Running the Application
```powershell
.\.venv\Scripts\python.exe main.py
```

## Cloud AI configuration

Open **Settings → Artificial Intelligence**, select a provider and save its Base URL, model and API key. For an OpenAI-compatible gateway, use the API base URL ending in `/v1`; only HTTPS endpoints are accepted. API keys are saved in the operating-system keyring and are never written to project JSON files.

## Build a Windows package

```powershell
.\.venv\Scripts\python.exe scripts\build.py
```

The build includes the static `web` assets needed by the PyWebView interface.

Operational backup, restore, delivery and recovery guidance is in [docs/OPERATIONS.md](docs/OPERATIONS.md).

## Running Tests and Quality Checks
```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy app
```
