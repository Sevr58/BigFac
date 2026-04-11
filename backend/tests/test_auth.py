def test_register_success(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "strongpass123",
        "full_name": "Test User"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data

def test_register_duplicate_email(client):
    payload = {"email": "test@example.com", "password": "pass123", "full_name": "User"}
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409

def test_login_success(client):
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com", "password": "pass123", "full_name": "User"
    })
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com", "password": "pass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com", "password": "pass123", "full_name": "User"
    })
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com", "password": "wrong"
    })
    assert response.status_code == 401

def test_get_me(client):
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com", "password": "pass123", "full_name": "User"
    })
    login = client.post("/api/v1/auth/login", json={
        "email": "test@example.com", "password": "pass123"
    })
    token = login.json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
