"""Enterprise MCP Gateway: the centralized control plane between the agents and the
state's enterprise tools. It mounts each FastMCP tool server's SSE ASGI app into the main
FastAPI application and enforces, server-side:

1. Connection-level JWT authentication — an unauthenticated caller can never reach
   tools/list or tools/call (JWTGateASGIMiddleware).
2. Identity-aware tools/list — the schema returned to the connected client is filtered to
   the tools the authenticated user's role may see, so agents never even learn that
   out-of-role tools exist. (The Agents SDK client applies the same policy again via
   MCPServerSse's tool_filter — see orchestrator.py — as defense in depth.)
3. Identity-aware tools/call — a call to an out-of-role tool is refused at the gateway
   even if a client bypasses the advertised schema.
4. DPDPA audit logging — every tool invocation (allowed, denied, or held) is written to
   the audit_logs table with actor, action, and purpose.
5. Human-in-the-loop holds — sensitive tools (access_policy.SENSITIVE_TOOLS_REQUIRING_APPROVAL)
   are not executed until a senior examiner approves the exact call via /tool-approvals.
"""

import hashlib
import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.auth.security import decode_access_token
from app.database import async_session_maker
from app.mcp_servers.access_policy import tool_allowed_for_role, tool_requires_approval
from app.mcp_servers.forensics_tools import forensics_mcp
from app.mcp_servers.gov_systems_tools import gov_systems_mcp
from app.mcp_servers.identity import MCPIdentity, current_mcp_identity
from app.mcp_servers.legal_tools import legal_mcp
from app.models.approval import ApprovalStatus, ToolApprovalRequest
from app.models.audit import AuditLog
from app.models.user import Role, User

MCP_SERVERS: dict[str, FastMCP] = {
    "legal": legal_mcp,
    "forensics": forensics_mcp,
    "gov-systems": gov_systems_mcp,
}


class JWTGateASGIMiddleware:
    """Rejects MCP SSE connections that do not present a valid FEMAS JWT bearer token,
    preventing unauthenticated/"shadow AI" access to any tool server, and binds the
    token's identity to the connection so MCP handlers can enforce per-user policy."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()
        token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else None

        if not token:
            response = JSONResponse({"detail": "Missing bearer token for MCP gateway"}, status_code=401)
            await response(scope, receive, send)
            return

        try:
            payload = decode_access_token(token)
            identity = MCPIdentity(
                username=payload["sub"],
                role=Role(payload["role"]),
                jurisdiction=payload.get("jurisdiction", ""),
            )
        except (ValueError, KeyError):
            response = JSONResponse({"detail": "Invalid or expired bearer token"}, status_code=401)
            await response(scope, receive, send)
            return

        # MCP handlers run inside this connection's task context, so they inherit this.
        reset_token = current_mcp_identity.set(identity)
        try:
            await self.app(scope, receive, send)
        finally:
            current_mcp_identity.reset(reset_token)


def _call_fingerprint(identity: MCPIdentity, tool_name: str, arguments: dict[str, Any]) -> str:
    canonical = json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(f"{identity.username}|{tool_name}|{canonical}".encode()).hexdigest()


async def _audit_tool_call(identity: MCPIdentity, action: str, tool_name: str, arguments: dict[str, Any]) -> None:
    """DPDPA accountability trail: one audit_logs row per tool invocation attempt."""
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.username == identity.username))
        actor = result.scalar_one_or_none()
        if actor is None:
            return  # token subject no longer exists; connection-level auth already logged 401s upstream
        db.add(
            AuditLog(
                actor_id=actor.id,
                actor_role=identity.role.value,
                action=action,
                resource_type="mcp_tool",
                purpose="agent tool execution",
                detail=f"{tool_name} args={json.dumps(arguments, default=str)[:2000]}",
            )
        )
        await db.commit()


async def _approval_gate(identity: MCPIdentity, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
    """Returns None when execution may proceed, or the structured hold/deny payload to
    send back to the agent instead of executing the tool."""
    fingerprint = _call_fingerprint(identity, tool_name, arguments)
    async with async_session_maker() as db:
        result = await db.execute(
            select(ToolApprovalRequest)
            .where(ToolApprovalRequest.fingerprint == fingerprint)
            .order_by(ToolApprovalRequest.requested_at.desc())
            .limit(1)
        )
        request = result.scalars().first()

        if request is not None and request.status == ApprovalStatus.APPROVED:
            return None
        if request is not None and request.status == ApprovalStatus.PENDING:
            return {
                "status": "approval_pending",
                "approval_request_id": request.id,
                "message": (
                    f"Execution of '{tool_name}' is held for human-in-the-loop sign-off. "
                    "A senior examiner must approve it via POST /tool-approvals/{id}/approve. "
                    "Report this to the user and continue without this tool's output."
                ),
            }
        if request is not None and request.status == ApprovalStatus.REJECTED:
            return {
                "status": "approval_rejected",
                "approval_request_id": request.id,
                "message": f"A senior examiner rejected this exact '{tool_name}' call. Do not retry it.",
            }

        request = ToolApprovalRequest(
            tool_name=tool_name,
            arguments_json=json.dumps(arguments, default=str),
            fingerprint=fingerprint,
            requested_by_username=identity.username,
        )
        db.add(request)
        await db.commit()
        return {
            "status": "approval_required",
            "approval_request_id": request.id,
            "message": (
                f"'{tool_name}' is a sensitive tool and was NOT executed. An approval request "
                "has been filed for a senior examiner; the workflow can be re-run after "
                "approval. Report this to the user and continue without this tool's output."
            ),
        }


async def list_tools_for_identity(server: FastMCP) -> list:
    """Server-side tools/list filtering: the connected user's role determines which tool
    schemas the gateway advertises at all."""
    identity = current_mcp_identity.get()
    if identity is None:
        return []
    tools = await server.list_tools()
    return [tool for tool in tools if tool_allowed_for_role(tool.name, identity.role)]


async def call_tool_with_policy(server: FastMCP, tool_name: str, arguments: dict[str, Any]) -> Any:
    """Server-side tools/call enforcement: role gate -> HITL hold -> audit -> execute."""
    identity = current_mcp_identity.get()
    if identity is None:
        return {"error": "No authenticated identity bound to this MCP connection", "code": "unauthenticated"}

    if not tool_allowed_for_role(tool_name, identity.role):
        await _audit_tool_call(identity, f"mcp_tool_denied:{tool_name}", tool_name, arguments)
        return {
            "error": f"Role '{identity.role.value}' is not authorized to invoke '{tool_name}'",
            "code": "role_denied",
        }

    if tool_requires_approval(tool_name):
        hold = await _approval_gate(identity, tool_name, arguments)
        if hold is not None:
            await _audit_tool_call(identity, f"mcp_tool_held:{tool_name}:{hold['status']}", tool_name, arguments)
            return hold

    await _audit_tool_call(identity, f"mcp_tool_call:{tool_name}", tool_name, arguments)
    return await server.call_tool(tool_name, arguments)


def _secure_server(server: FastMCP) -> None:
    """Re-registers the low-level tools/list and tools/call handlers with the gateway's
    identity-aware wrappers (which delegate to the FastMCP defaults after the checks)."""

    @server._mcp_server.list_tools()
    async def _identity_filtered_list_tools():  # noqa: ANN202
        return await list_tools_for_identity(server)

    @server._mcp_server.call_tool()
    async def _policy_checked_call_tool(tool_name: str, arguments: dict[str, Any]):  # noqa: ANN202
        return await call_tool_with_policy(server, tool_name, arguments)


for _server in MCP_SERVERS.values():
    _secure_server(_server)


def build_mcp_asgi_app(server: FastMCP) -> ASGIApp:
    # Deliberately do not pass mount_path here: when this app is mounted under a prefix
    # via Starlette's app.mount(), the ASGI root_path is set automatically and the MCP SSE
    # transport already concatenates root_path + endpoint itself (see
    # mcp.server.sse.SseServerTransport.connect_sse). Passing mount_path too would double
    # the prefix (e.g. "/mcp/legal/mcp/legal/messages/").
    return JWTGateASGIMiddleware(server.sse_app())
