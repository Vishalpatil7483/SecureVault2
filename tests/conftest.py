"""
Shared pytest fixtures.

Each test gets a freshly-built app on the `testing` config with an isolated
in-memory database, so tests never touch the real dev database and cannot
interfere with one another.
"""
import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
