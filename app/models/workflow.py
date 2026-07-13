import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WorkflowStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED_BY_GUARDRAIL = "blocked_by_guardrail"


class WorkflowRun(Base):
    """One execution of the Triage -> Digital Forensics -> Legal Compliance -> Reporting pipeline."""

    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"))
    evidence_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("evidence.id"), nullable=True)
    initiated_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    status: Mapped[WorkflowStatus] = mapped_column(Enum(WorkflowStatus), default=WorkflowStatus.RUNNING)
    final_output: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    steps: Mapped[list["WorkflowStep"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class WorkflowStep(Base):
    """A single traced event within a run: agent turn, tool call, or handoff."""

    __tablename__ = "workflow_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_runs.id"))
    sequence: Mapped[int] = mapped_column(Integer)
    step_type: Mapped[str] = mapped_column(String(32))  # agent_turn | tool_call | handoff | guardrail
    agent_name: Mapped[str] = mapped_column(String(128), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    run: Mapped["WorkflowRun"] = relationship(back_populates="steps")
