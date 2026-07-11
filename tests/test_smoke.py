"""
Basic smoke tests — proof the scaffolding and auth wiring work end-to-end.
Extensive coverage is intentionally deferred to a later milestone.
"""


def test_index_ok(client):
    assert client.get("/").status_code == 200


def test_login_page_ok(client):
    assert client.get("/auth/login").status_code == 200


def test_security_headers_present(client):
    resp = client.get("/")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Content-Security-Policy" in resp.headers


def test_register_creates_user(client, app):
    resp = client.post(
        "/auth/register",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "password": "supersecret1",
            "confirm": "supersecret1",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    from app.auth.models import User

    with app.app_context():
        assert User.query.filter_by(username="alice").first() is not None
