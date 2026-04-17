import pytest


@pytest.fixture
async def auth_client(client):
    r = await client.post(
        "/api/auth/register",
        json={"email": "quiz@example.com", "password": "pass123", "name": "Quizzer"},
    )
    token = r.json()["data"]["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
async def deck_with_words(auth_client):
    r = await auth_client.post(
        "/api/decks",
        json={"name": "Spanish Basics", "source_lang": "en", "target_lang": "es"},
    )
    deck_id = r.json()["data"]["id"]
    words = [
        ("hello", "hola"),
        ("cat", "gato"),
        ("dog", "perro"),
        ("water", "agua"),
        ("house", "casa"),
    ]
    word_ids = []
    for term, translation in words:
        r = await auth_client.post(
            f"/api/decks/{deck_id}/words",
            json={"term": term, "translation": translation},
        )
        word_ids.append(r.json()["data"]["id"])
    return auth_client, deck_id, word_ids, words


@pytest.mark.asyncio
async def test_start_quiz_returns_cards(deck_with_words):
    client, deck_id, word_ids, _ = deck_with_words
    r = await client.post("/api/quiz/start", json={"deck_id": deck_id, "count": 3})
    assert r.status_code == 200
    cards = r.json()["data"]
    assert len(cards) == 3
    for card in cards:
        assert "card_id" in card
        assert "prompt" in card
        assert card["direction"] == "term_to_translation"


@pytest.mark.asyncio
async def test_start_quiz_fewer_words_than_count(deck_with_words):
    client, deck_id, _, _ = deck_with_words
    r = await client.post("/api/quiz/start", json={"deck_id": deck_id, "count": 100})
    assert r.status_code == 200
    cards = r.json()["data"]
    assert len(cards) == 5


@pytest.mark.asyncio
async def test_start_quiz_requires_auth(client):
    r = await client.post("/api/quiz/start", json={"deck_id": 1, "count": 5})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_start_quiz_wrong_user(auth_client, client):
    r = await client.post(
        "/api/auth/register",
        json={"email": "other@example.com", "password": "pass123", "name": "Other"},
    )
    other_token = r.json()["data"]["token"]
    r = await client.post(
        "/api/decks",
        json={"name": "Other Deck", "source_lang": "en", "target_lang": "fr"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    other_deck_id = r.json()["data"]["id"]

    r = await auth_client.post("/api/quiz/start", json={"deck_id": other_deck_id, "count": 5})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_answer_correct(deck_with_words):
    client, deck_id, word_ids, words = deck_with_words
    hello_id = word_ids[0]
    r = await client.post("/api/quiz/answer", json={"word_id": hello_id, "answer": "hola"})
    assert r.status_code == 200
    result = r.json()["data"]
    assert result["correct"] is True
    assert result["expected"] == "hola"
    assert result["word_id"] == hello_id


@pytest.mark.asyncio
async def test_answer_correct_case_insensitive(deck_with_words):
    client, deck_id, word_ids, _ = deck_with_words
    hello_id = word_ids[0]
    r = await client.post("/api/quiz/answer", json={"word_id": hello_id, "answer": "  HOLA  "})
    assert r.status_code == 200
    assert r.json()["data"]["correct"] is True


@pytest.mark.asyncio
async def test_answer_wrong(deck_with_words):
    client, deck_id, word_ids, _ = deck_with_words
    hello_id = word_ids[0]
    r = await client.post("/api/quiz/answer", json={"word_id": hello_id, "answer": "nope"})
    assert r.status_code == 200
    result = r.json()["data"]
    assert result["correct"] is False
    assert result["expected"] == "hola"


@pytest.mark.asyncio
async def test_wrong_answer_sets_mastered_false(deck_with_words):
    client, deck_id, word_ids, _ = deck_with_words
    hello_id = word_ids[0]
    for _ in range(5):
        await client.post("/api/quiz/answer", json={"word_id": hello_id, "answer": "hola"})

    r = await client.get(f"/api/quiz/results/{deck_id}")
    stats = r.json()["data"]
    hello_stat = next(s for s in stats if s["word_id"] == hello_id)
    assert hello_stat["mastered"] is True

    await client.post("/api/quiz/answer", json={"word_id": hello_id, "answer": "wrong"})
    r = await client.get(f"/api/quiz/results/{deck_id}")
    stats = r.json()["data"]
    hello_stat = next(s for s in stats if s["word_id"] == hello_id)
    assert hello_stat["mastered"] is False


@pytest.mark.asyncio
async def test_mastery_after_5_correct(deck_with_words):
    client, deck_id, word_ids, _ = deck_with_words
    hello_id = word_ids[0]

    for i in range(4):
        r = await client.post("/api/quiz/answer", json={"word_id": hello_id, "answer": "hola"})
        assert r.json()["data"]["correct"] is True

    r = await client.get(f"/api/quiz/results/{deck_id}")
    stats = r.json()["data"]
    hello_stat = next(s for s in stats if s["word_id"] == hello_id)
    assert hello_stat["mastered"] is False
    assert hello_stat["times_correct"] == 4

    r = await client.post("/api/quiz/answer", json={"word_id": hello_id, "answer": "hola"})
    assert r.json()["data"]["correct"] is True

    r = await client.get(f"/api/quiz/results/{deck_id}")
    stats = r.json()["data"]
    hello_stat = next(s for s in stats if s["word_id"] == hello_id)
    assert hello_stat["mastered"] is True
    assert hello_stat["times_correct"] == 5


@pytest.mark.asyncio
async def test_quiz_results(deck_with_words):
    client, deck_id, word_ids, words = deck_with_words
    hello_id = word_ids[0]
    await client.post("/api/quiz/answer", json={"word_id": hello_id, "answer": "hola"})
    await client.post("/api/quiz/answer", json={"word_id": hello_id, "answer": "wrong"})

    r = await client.get(f"/api/quiz/results/{deck_id}")
    assert r.status_code == 200
    stats = r.json()["data"]
    assert len(stats) == 5
    hello_stat = next(s for s in stats if s["word_id"] == hello_id)
    assert hello_stat["times_correct"] == 1
    assert hello_stat["times_wrong"] == 1
    assert hello_stat["term"] == "hello"
    assert hello_stat["translation"] == "hola"


@pytest.mark.asyncio
async def test_quiz_results_requires_auth(client):
    r = await client.get("/api/quiz/results/1")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_answer_wrong_user_word(auth_client, client):
    r = await client.post(
        "/api/auth/register",
        json={"email": "other2@example.com", "password": "pass123", "name": "Other2"},
    )
    other_token = r.json()["data"]["token"]
    r = await client.post(
        "/api/decks",
        json={"name": "Other Deck", "source_lang": "en", "target_lang": "fr"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    other_deck_id = r.json()["data"]["id"]
    r = await client.post(
        f"/api/decks/{other_deck_id}/words",
        json={"term": "bonjour", "translation": "hello"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    other_word_id = r.json()["data"]["id"]

    r = await auth_client.post(
        "/api/quiz/answer", json={"word_id": other_word_id, "answer": "hello"}
    )
    assert r.status_code == 404
