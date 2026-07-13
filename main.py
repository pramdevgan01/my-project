from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from app.agents_system.model_provider import configure_model_provider
from app.auth.security import hash_password
from app.database import async_session_maker, init_db
from app.mcp_servers.gateway import MCP_SERVERS, build_mcp_asgi_app
from app.models.user import Role, User
from app.routers import auth, audit, cases, certificates, evidence, workflows

configure_model_provider()


async def _seed_default_admin() -> None:
    """Creates a first admin account (username: admin) if no users exist yet, so the API
    is usable out of the box. Change this password immediately in any real deployment."""
    async with async_session_maker() as db:
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none() is not None:
            return
        db.add(
            User(
                username="admin",
                full_name="FEMAS Administrator",
                hashed_password=hash_password("ChangeMe123!"),
                role=Role.ADMIN,
                jurisdiction="ALL",
                badge_number="ADMIN-000",
            )
        )
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _seed_default_admin()
    yield


app = FastAPI(
    title="FEMAS - Forensic Evidence Multi-Agent System",
    description=(
        "Backend for an enterprise multi-agent forensic evidence management system: "
        "FastAPI REST API, OpenAI Agents SDK orchestration, and MCP tool servers "
        "(mounted below at /mcp/*) implementing BSA 2023 Section 63 compliance."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(evidence.router)
app.include_router(certificates.router)
app.include_router(workflows.router)
app.include_router(audit.router)

for _key, _server in MCP_SERVERS.items():
    app.mount(f"/mcp/{_key}", build_mcp_asgi_app(_server))


@app.get("/")
async def root():
    return {"message": "FEMAS backend is running", "docs": "/docs", "mcp_servers": list(MCP_SERVERS.keys())}
