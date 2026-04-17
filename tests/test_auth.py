import pytest


@pytest.mark.asyncio
async def test_register(client):
    r = await client.post("/api/auth/register", json={"email": "Alice@Test.com", "password": "secret", "name": "Alice"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert "token" in data
    assert data["token"]


@pytest.mark.asyncio
async def test_register_normalizes_email(client):
    r = await client.post("/api/auth/register", json={"email": "BOB@TEST.COM", "password": "pass", "name": "Bob"})
    assert r.status_code == 200
    r2 = await client.post("/api/auth/login", json={"email": "bob@test.com", "password": "pass"})
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_duplicate_email(client):
    await client.post("/api/auth/register", json={"email": "dup@test.com", "password": "p", "name": "D"})
    r = await client.post("/api/auth/register", json={"email": "dup@test.com", "password": "p", "name": "D2"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login(client):
    await client.post("/api/auth/register", json={"email": "login@test.com", "password": "mypass", "name": "L"})
    r = await client.post("/api/auth/login", json={"email": "login@test.com", "password": "mypass"})
    assert r.status_code == 200
    assert r.json()["data"]["token"]


@pytest.mark.asyncio
async def test_wrong_password(client):
    await client.post("/api/auth/register", json={"email": "wp@test.com", "password": "correct", "name": "W"})
    r = await client.post("/api/auth/login", json={"email": "wp@test.com", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client):
    reg = await client.post("/api/auth/register", json={"email": "me@test.com", "password": "pw", "name": "Me"})
    token = reg.json()["data"]["token"]
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["email"] == "me@test.com"
    assert data["display_name"] == "Me"
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_me_no_token(client):
    r = await client.get("/api/auth/me")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    r = await client.get("/api/auth/me", headers={"Authorization": "Bearer notavalidtoken"})
    assert r.status_code == 401
