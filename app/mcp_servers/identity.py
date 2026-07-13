"""Per-connection identity for the Enterprise MCP Gateway.

The JWT gate middleware in gateway.py decodes the bearer token presented when the MCP
SSE connection is established and stashes the caller's identity in a ContextVar. MCP
request handlers (tools/list, tools/call) execute inside that connection's task context,
so they can read the identity back without any protocol changes — giving the gateway
server-side, identity-aware behavior instead of trusting the agent client to filter.
"""

from contextvars import ContextVar
from dataclasses import dataclass

from app.models.user import Role


@dataclass(frozen=True)
class MCPIdentity:
    username: str
    role: Role
    jurisdiction: str


current_mcp_identity: ContextVar[MCPIdentity | None] = ContextVar("current_mcp_identity", default=None)
