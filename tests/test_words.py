import pytest


async def _register(client, email="words@test.com"):
    r = await client.post("/api/auth/register", json={"email": email, "password": "pass123", "name": "Tester"})
    return r.json()["data"]["token"]


@pytest.mark.asyncio
async def test_create_deck(client):
    token = await _register(client)
    r = await client.post(
        "/api/decks",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Spanish Basics", "source_lang": "en", "target_lang": "es"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["name"] == "Spanish Basics"
    assert data["source_lang"] == "en"
    assert data["target_lang"] == "es"
    assert data["word_count"] == 0


@pytest.mark.asyncio
async def test_list_decks(client):
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    await client.post("/api/decks", headers=h, json={"name": "Deck A", "source_lang": "en", "target_lang": "fr"})
    await client.post("/api/decks", headers=h, json={"name": "Deck B", "source_lang": "en", "target_lang": "de"})
    r = await client.get("/api/decks", headers=h)
    assert r.status_code == 200
    assert len(r.json()["data"]) == 2


@pytest.mark.asyncio
async def test_get_deck(client):
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    cr = await client.post("/api/decks", headers=h, json={"name": "Test", "source_lang": "en", "target_lang": "es"})
    deck_id = cr.json()["data"]["id"]
    r = await client.get(f"/api/decks/{deck_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["id"] == deck_id


@pytest.mark.asyncio
async def test_deck_not_found(client):
    token = await _register(client)
    r = await client.get("/api/decks/9999", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_add_word(client):
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    cr = await client.post("/api/decks", headers=h, json={"name": "Test", "source_lang": "en", "target_lang": "es"})
    deck_id = cr.json()["data"]["id"]
    r = await client.post(f"/api/decks/{deck_id}/words", headers=h, json={"term": "hello", "translation": "hola"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["term"] == "hello"
    assert data["translation"] == "hola"
    assert data["mastered"] is False


@pytest.mark.asyncio
async def test_duplicate_term_returns_409(client):
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    cr = await client.post("/api/decks", headers=h, json={"name": "Test", "source_lang": "en", "target_lang": "es"})
    deck_id = cr.json()["data"]["id"]
    await client.post(f"/api/decks/{deck_id}/words", headers=h, json={"term": "hello", "translation": "hola"})
    r = await client.post(f"/api/decks/{deck_id}/words", headers=h, json={"term": "hello", "translation": "hola2"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_list_words(client):
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    cr = await client.post("/api/decks", headers=h, json={"name": "Test", "source_lang": "en", "target_lang": "es"})
    deck_id = cr.json()["data"]["id"]
    await client.post(f"/api/decks/{deck_id}/words", headers=h, json={"term": "one", "translation": "uno"})
    await client.post(f"/api/decks/{deck_id}/words", headers=h, json={"term": "two", "translation": "dos"})
    r = await client.get(f"/api/decks/{deck_id}/words", headers=h)
    assert r.status_code == 200
    assert len(r.json()["data"]) == 2


@pytest.mark.asyncio
async def test_update_word(client):
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    cr = await client.post("/api/decks", headers=h, json={"name": "Test", "source_lang": "en", "target_lang": "es"})
    deck_id = cr.json()["data"]["id"]
    wr = await client.post(f"/api/decks/{deck_id}/words", headers=h, json={"term": "hello", "translation": "hola"})
    word_id = wr.json()["data"]["id"]
    r = await client.put(f"/api/decks/{deck_id}/words/{word_id}", headers=h, json={"translation": "¡hola!"})
    assert r.status_code == 200
    assert r.json()["data"]["translation"] == "¡hola!"
    assert r.json()["data"]["term"] == "hello"


@pytest.mark.asyncio
async def test_delete_word(client):
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    cr = await client.post("/api/decks", headers=h, json={"name": "Test", "source_lang": "en", "target_lang": "es"})
    deck_id = cr.json()["data"]["id"]
    wr = await client.post(f"/api/decks/{deck_id}/words", headers=h, json={"term": "hello", "translation": "hola"})
    word_id = wr.json()["data"]["id"]
    r = await client.delete(f"/api/decks/{deck_id}/words/{word_id}", headers=h)
    assert r.status_code == 200
    words = await client.get(f"/api/decks/{deck_id}/words", headers=h)
    assert len(words.json()["data"]) == 0


@pytest.mark.asyncio
async def test_delete_deck_cascades(client):
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    cr = await client.post("/api/decks", headers=h, json={"name": "Test", "source_lang": "en", "target_lang": "es"})
    deck_id = cr.json()["data"]["id"]
    await client.post(f"/api/decks/{deck_id}/words", headers=h, json={"term": "hello", "translation": "hola"})
    r = await client.delete(f"/api/decks/{deck_id}", headers=h)
    assert r.status_code == 200
    r2 = await client.get(f"/api/decks/{deck_id}", headers=h)
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_deck_isolation(client):
    token_a = await _register(client, "user_a@test.com")
    token_b = await _register(client, "user_b@test.com")
    ha = {"Authorization": f"Bearer {token_a}"}
    hb = {"Authorization": f"Bearer {token_b}"}
    cr = await client.post("/api/decks", headers=ha, json={"name": "A's Deck", "source_lang": "en", "target_lang": "es"})
    deck_id = cr.json()["data"]["id"]
    r = await client.get(f"/api/decks/{deck_id}", headers=hb)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_word_count_in_deck(client):
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    cr = await client.post("/api/decks", headers=h, json={"name": "Test", "source_lang": "en", "target_lang": "es"})
    deck_id = cr.json()["data"]["id"]
    await client.post(f"/api/decks/{deck_id}/words", headers=h, json={"term": "one", "translation": "uno"})
    await client.post(f"/api/decks/{deck_id}/words", headers=h, json={"term": "two", "translation": "dos"})
    r = await client.get(f"/api/decks/{deck_id}", headers=h)
    assert r.json()["data"]["word_count"] == 2
