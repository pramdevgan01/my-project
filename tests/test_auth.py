import pytest

from app.auth.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models.user import Role, User


def test_password_hash_roundtrip():
    hashed = hash_password("Sup3rSecret!")
    assert verify_password("Sup3rSecret!", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    token = create_access_token(subject="officer1", role="officer", jurisdiction="Delhi")
    payload = decode_access_token(token)
    assert payload["sub"] == "officer1"
    assert payload["role"] == "officer"
    assert payload["jurisdiction"] == "Delhi"


def test_decode_invalid_token_raises():
    with pytest.raises(ValueError):
        decode_access_token("not-a-real-token")


async def _create_user(db_session, username, role, jurisdiction="Delhi", password="Passw0rd!"):
    user = User(
        username=username,
        full_name=username.title(),
        hashed_password=hash_password(password),
        role=role,
        jurisdiction=jurisdiction,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_login_and_me(client, db_session):
    await _create_user(db_session, "officer1", Role.OFFICER)

    login_resp = await client.post("/auth/login", data={"username": "officer1", "password": "Passw0rd!"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "officer1"
    assert me_resp.json()["role"] == "officer"


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client, db_session):
    await _create_user(db_session, "officer2", Role.OFFICER)
    resp = await client.post("/auth/login", data={"username": "officer2", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_requires_admin_role(client, db_session):
    await _create_user(db_session, "officer3", Role.OFFICER)
    login_resp = await client.post("/auth/login", data={"username": "officer3", "password": "Passw0rd!"})
    token = login_resp.json()["access_token"]

    resp = await client.post(
        "/auth/register",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "newuser",
            "full_name": "New User",
            "password": "Passw0rd!",
            "role": "officer",
            "jurisdiction": "Delhi",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_register_user(client, db_session):
    await _create_user(db_session, "admin1", Role.ADMIN, jurisdiction="ALL")
    login_resp = await client.post("/auth/login", data={"username": "admin1", "password": "Passw0rd!"})
    token = login_resp.json()["access_token"]

    resp = await client.post(
        "/auth/register",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "newofficer",
            "full_name": "New Officer",
            "password": "Passw0rd!",
            "role": "officer",
            "jurisdiction": "Delhi",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "newofficer"
