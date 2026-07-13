import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ToolApprovalRequest(Base):
    """Human-in-the-loop gate for sensitive MCP tools: when an agent invokes a tool listed
    in access_policy.SENSITIVE_TOOLS_REQUIRING_APPROVAL, the gateway records the exact
    call (tool + arguments + requester) here as PENDING and refuses to execute it. A
    senior examiner (nodal officer / admin) approves or rejects via /tool-approvals; only
    a re-run whose call matches the approved fingerprint exactly will then execute."""

    __tablename__ = "tool_approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tool_name: Mapped[str] = mapped_column(String(128))
    arguments_json: Mapped[str] = mapped_column(Text, default="{}")
    # sha256 over (requester, tool, canonical arguments): an approval never authorizes a
    # different caller or different arguments than the ones the human actually reviewed.
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    requested_by_username: Mapped[str] = mapped_column(String(64))

    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    decided_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision_note: Mapped[str] = mapped_column(Text, default="")
