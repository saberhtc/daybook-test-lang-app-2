import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client_with_user(set_test_db):
    from app import app
    from db import init_db

    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/auth/register",
            json={"email": "progress@test.com", "password": "pass123", "name": "Tracker"},
        )
        token = r.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}
        yield ac, headers


@pytest.mark.asyncio
async def test_stats_no_data(client_with_user):
    client, headers = client_with_user
    r = await client.get("/api/progress/stats", headers=headers)
    assert r.status_code == 200
    stats = r.json()["data"]
    assert stats["total_words"] == 0
    assert stats["mastered_words"] == 0
    assert stats["total_quizzes"] == 0
    assert stats["overall_accuracy_pct"] == 0.0
    assert stats["current_streak_days"] == 0
    assert stats["longest_streak_days"] == 0


@pytest.mark.asyncio
async def test_stats_after_quiz(client_with_user):
    client, headers = client_with_user

    r = await client.post(
        "/api/decks",
        headers=headers,
        json={"name": "French", "source_lang": "en", "target_lang": "fr"},
    )
    deck_id = r.json()["data"]["id"]

    await client.post(f"/api/decks/{deck_id}/words", headers=headers, json={"term": "hello", "translation": "bonjour"})
    await client.post(f"/api/decks/{deck_id}/words", headers=headers, json={"term": "water", "translation": "eau"})

    r = await client.post("/api/quiz/start", headers=headers, json={"deck_id": deck_id, "count": 2})
    cards = r.json()["data"]

    for card in cards:
        await client.post(
            "/api/quiz/answer",
            headers=headers,
            json={"word_id": card["card_id"], "answer": "bonjour"},
        )

    r = await client.get("/api/progress/stats", headers=headers)
    assert r.status_code == 200
    stats = r.json()["data"]
    assert stats["total_words"] == 2
    assert stats["total_quizzes"] == 2
    assert stats["current_streak_days"] >= 1
    assert stats["longest_streak_days"] >= 1
    assert 0.0 <= stats["overall_accuracy_pct"] <= 100.0


@pytest.mark.asyncio
async def test_history_returns_30_days(client_with_user):
    client, headers = client_with_user

    r = await client.get("/api/progress/history", headers=headers)
    assert r.status_code == 200
    history = r.json()["data"]
    assert len(history) == 30

    for entry in history:
        assert "date" in entry
        assert entry["quizzes_completed"] == 0
        assert entry["correct_count"] == 0
        assert entry["total_count"] == 0
        assert entry["accuracy_pct"] == 0.0


@pytest.mark.asyncio
async def test_history_after_quiz(client_with_user):
    client, headers = client_with_user

    r = await client.post(
        "/api/decks",
        headers=headers,
        json={"name": "Spanish", "source_lang": "en", "target_lang": "es"},
    )
    deck_id = r.json()["data"]["id"]
    await client.post(f"/api/decks/{deck_id}/words", headers=headers, json={"term": "yes", "translation": "si"})

    r = await client.post("/api/quiz/start", headers=headers, json={"deck_id": deck_id, "count": 1})
    card = r.json()["data"][0]
    await client.post(
        "/api/quiz/answer",
        headers=headers,
        json={"word_id": card["card_id"], "answer": "si"},
    )

    r = await client.get("/api/progress/history", headers=headers)
    history = r.json()["data"]
    assert len(history) == 30

    today_entry = history[-1]
    assert today_entry["quizzes_completed"] >= 1
    assert today_entry["total_count"] >= 1


@pytest.mark.asyncio
async def test_streak_calculation(client_with_user):
    client, headers = client_with_user

    r = await client.post(
        "/api/decks",
        headers=headers,
        json={"name": "Deck", "source_lang": "en", "target_lang": "de"},
    )
    deck_id = r.json()["data"]["id"]
    await client.post(f"/api/decks/{deck_id}/words", headers=headers, json={"term": "one", "translation": "ein"})

    r = await client.post("/api/quiz/start", headers=headers, json={"deck_id": deck_id, "count": 1})
    card = r.json()["data"][0]
    await client.post(
        "/api/quiz/answer",
        headers=headers,
        json={"word_id": card["card_id"], "answer": "ein"},
    )

    r = await client.get("/api/progress/stats", headers=headers)
    stats = r.json()["data"]
    assert stats["current_streak_days"] == 1
    assert stats["longest_streak_days"] == 1


@pytest.mark.asyncio
async def test_stats_require_auth(client_with_user):
    client, _ = client_with_user
    r = await client.get("/api/progress/stats")
    assert r.status_code == 401

    r = await client.get("/api/progress/history")
    assert r.status_code == 401
