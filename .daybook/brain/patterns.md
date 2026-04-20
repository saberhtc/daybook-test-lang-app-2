# Code Patterns

## Naming
- Files: snake_case (quiz.py, words.py)
- Functions: snake_case (get_user_words)
- Classes: PascalCase (WordCreate)
- Tables: snake_case, plural (words, quiz_attempts)
- API routes: kebab-case (/api/words, /api/quiz/start)

## API Design
- All endpoints under /api/
- Response shape: {"data": ..., "error": null}
- Error response: {"data": null, "error": "message"}
- Use async def for all route handlers
- Authentication via Bearer JWT token in Authorization header
- Protected routes use Depends(get_current_user)
- List endpoints return arrays in data field
- Create endpoints return the created object
- IDs are integers, auto-incrementing

## Database
- All tables have: id INTEGER PRIMARY KEY AUTOINCREMENT
- All tables have: created_at TEXT DEFAULT (datetime('now'))
- Use IF NOT EXISTS on all CREATE TABLE
- Use aiosqlite with WAL mode enabled
- PRAGMA foreign_keys = ON on every connection
- Use DB_PATH environment variable for database location
- Use get_db() for connection management

## Frontend
- Single static/index.html file
- Vanilla JS, no frameworks
- Fetch API for all HTTP calls
- Dark theme preferred
- Mobile-responsive

## Error Handling
- 400 for validation errors
- 401 for missing or invalid auth
- 404 for not found
- 409 for duplicates (e.g. same word in same deck)

## Testing
- Use pytest with pytest-asyncio
- Use httpx.AsyncClient with ASGITransport for API tests
- Fixtures in conftest.py
- Test file naming: tests/test_feature.py
- All database paths must read from DB_PATH env var
