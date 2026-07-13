import os
import shutil
from pathlib import Path

TEST_DIR = Path(__file__).parent
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DIR}/test_femas.db")
os.environ.setdefault("EVIDENCE_STORAGE_DIR", str(TEST_DIR / "test_evidence_store"))
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("OPENROUTER_API_KEY", "sk-or-test-not-a-real-key")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import Base, async_session_maker, engine
from app.models import audit, case, certificate, evidence, user, workflow  # noqa: F401


@pytest_asyncio.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_maker() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    import main as main_module

    async def _override_get_db():
        yield db_session

    from app.database import get_db

    main_module.app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    main_module.app.dependency_overrides.clear()


@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_artifacts():
    yield
    for path in [TEST_DIR / "test_femas.db", TEST_DIR / "test_evidence_store"]:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink()
