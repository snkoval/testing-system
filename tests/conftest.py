import os
import tempfile

import pytest

from app import create_app, db
from app.config import TestConfig


@pytest.fixture
def tests_folder():
    d = tempfile.mkdtemp()
    yield d


@pytest.fixture
def app(tests_folder):
    app = create_app(TestConfig)
    app.config['TESTS_FOLDER'] = tests_folder
    os.makedirs(tests_folder, exist_ok=True)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
