# mcubin

A fast, minimalist desktop inventory system for electronic parts.

## Features

- Barcode scanner-first part entry
- SQLite-backed storage with Alembic migrations (schema changes are safe)
- Clean dark UI
- Mouser / DigiKey lookup *(coming soon)*

## Requirements

- Python 3.11+
- Linux / macOS / Windows

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install PySide6 SQLAlchemy alembic
```

## Run

```bash
PYTHONPATH=. .venv/bin/python main.py
```

The database is stored at `~/.mcubin/inventory.db` and migrations run automatically on launch.

## Schema changes

```bash
# After editing mcubin/models.py:
PYTHONPATH=. .venv/bin/alembic revision --autogenerate -m "describe change"
PYTHONPATH=. .venv/bin/alembic upgrade head
```
