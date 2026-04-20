# Tech Stack

Python 3.12, FastAPI, SQLite (aiosqlite), single HTML frontend, JWT auth.

## File Structure
```
app.py              — FastAPI application entry point
db.py               — database init, tables, helpers
auth.py             — JWT authentication (register, login, get_current_user)
models.py           — Pydantic request/response models
words.py            — word/deck CRUD routes
quiz.py             — quiz logic and routes
progress.py         — stats and streak routes
static/index.html   — single-page frontend
requirements.txt    — Python dependencies
tests/              — pytest test suite
tests/conftest.py   — shared fixtures
```

## Dev Setup
```bash
pip install fastapi uvicorn aiosqlite pyjwt bcrypt httpx pytest pytest-asyncio --break-system-packages
```

## Run
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```
Port: 8000

## Test
```bash
python3 -m pytest tests/ -v
```
