# Project OS

Project OS is a Local-First desktop application for network and security deployment engineers.

## Features (Phase 1)
- Workspace Foundation
- Application settings (theme, workspace roots)
- Atomic JSON write for data safety
- Project discovery and background scanning
- CustomTkinter UI

## Setup
1. Ensure Python 3.11+ is installed.
2. Install dependencies: `pip install -r requirements.txt`
3. For development, install dev dependencies: `pip install -r requirements-dev.txt`

## Running the Application
```powershell
python main.py
```

## Running Tests and Quality Checks
```powershell
python -m pytest
python -m ruff check .
python -m mypy app
```
