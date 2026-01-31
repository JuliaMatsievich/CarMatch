"""Tests for auth API endpoints."""
import pytest
from fastapi.testclient import TestClient


def test_register_success(client: TestClient):
    """Регистрация нового пользователя возвращает 201 и токен."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert data["user"]["email"] == "user@example.com"
    assert "id" in data["user"]


def test_register_duplicate_email(client: TestClient):
    """Повторная регистрация с тем же email возвращает 400."""
    payload = {"email": "dup@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "уже зарегистрирован" in response.json()["detail"]


def test_register_validation_email(client: TestClient):
    """Невалидный email возвращает 422."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "invalid", "password": "password123"},
    )
    assert response.status_code == 422


def test_register_validation_password(client: TestClient):
    """Пароль короче 8 символов возвращает 422."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_login_success(client: TestClient):
    """Вход по зарегистрированным данным возвращает 200 и токен."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "mypassword"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "mypassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert data["user"]["email"] == "login@example.com"


def test_login_wrong_password(client: TestClient):
    """Неверный пароль возвращает 401."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "correctpass"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "Неверный" in response.json()["detail"]


def test_login_unknown_email(client: TestClient):
    """Вход с несуществующим email возвращает 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "password123"},
    )
    assert response.status_code == 401
