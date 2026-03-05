# mcubin

Desktop inventory system for electronic parts. Python + PySide6 + SQLAlchemy + Alembic.

## Run

```bash
PYTHONPATH=. .venv/bin/python main.py
```

## Schema changes

After editing `mcubin/models.py`:

```bash
PYTHONPATH=. .venv/bin/alembic revision --autogenerate -m "describe change"
PYTHONPATH=. .venv/bin/alembic upgrade head
```

Migrations run automatically on app launch.

## Conventions

- **No co-author line in git commits**
- No inline styles — all styles go in `mcubin/ui/theme.py` using objectName selectors
- Alembic for all schema changes — never manually alter the DB
- DB stored at `~/.mcubin/inventory.db`
