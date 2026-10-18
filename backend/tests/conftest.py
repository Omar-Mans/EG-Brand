import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db",
    "AI_MODE": "mock",
    "SOCIAL_MODE": "mock",
    "EMBEDDED_WORKER": "false",
    "UPLOAD_DIR": f"{_tmp}/uploads",
    "ADMIN_EMAILS": "admin@egbrand.test",
})

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c


def register(client, email="owner@cafe.test", company="قهوة نورا"):
    r = client.post("/api/auth/register", json={"company_name": company, "name": "عمر", "email": email, "password": "secret-pass-1"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}
