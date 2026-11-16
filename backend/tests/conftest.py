import pytest
from fastapi.testclient import TestClient
from app.core import storage
from app.main import app
from app.services import compiler

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'ROOT', tmp_path / 'data')
    monkeypatch.setattr(storage, 'PROJECTS', tmp_path / 'workspace')
    compiler.jobs.clear()
    with TestClient(app) as client:
        yield client
