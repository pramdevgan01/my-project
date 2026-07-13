import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EvidenceType(str, enum.Enum):
    MOBILE_EXTRACTION = "mobile_extraction"
    CALL_DETAIL_RECORD = "call_detail_record"
    CCTV_FOOTAGE = "cctv_footage"
    SERVER_LOG = "server_log"
    CHAT_EXPORT = "chat_export"
    DOCUMENT = "document"
    OTHER = "other"


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"))
    evidence_type: Mapped[EvidenceType] = mapped_column(Enum(EvidenceType))
    original_filename: Mapped[str] = mapped_column(String(256))
    storage_path: Mapped[str] = mapped_column(String(512))
    device_model: Mapped[str] = mapped_column(String(128), default="")
    device_imei: Mapped[str] = mapped_column(String(64), default="")
    device_os: Mapped[str] = mapped_column(String(128), default="")
    sha256_hash: Mapped[str] = mapped_column(String(64), default="")
    md5_hash: Mapped[str] = mapped_column(String(32), default="")
    uploaded_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    case: Mapped["Case"] = relationship(back_populates="evidence_items")
    custody_events: Mapped[list["ChainOfCustodyEvent"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan"
    )


class ChainOfCustodyEvent(Base):
    __tablename__ = "chain_of_custody_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evidence_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence.id"))
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(128))
    notes: Mapped[str] = mapped_column(Text, default="")
    integrity_hash_at_event: Mapped[str] = mapped_column(String(64), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    evidence: Mapped["Evidence"] = relationship(back_populates="custody_events")
