import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CertificateStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class BSACertificate(Base):
    """Section 63(4) BSA 2023 dual-part certificate for a piece of electronic evidence."""

    __tablename__ = "bsa_certificates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evidence_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence.id"))
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"))

    # Part A - person in charge of the device, lawful control declaration
    part_a_declarant_name: Mapped[str] = mapped_column(String(128), default="")
    part_a_device_particulars: Mapped[str] = mapped_column(Text, default="")
    part_a_lawful_control_statement: Mapped[str] = mapped_column(Text, default="")

    # Part B - technical expert verification
    part_b_expert_name: Mapped[str] = mapped_column(String(128), default="")
    part_b_hash_algorithm: Mapped[str] = mapped_column(String(16), default="SHA-256")
    part_b_hash_value: Mapped[str] = mapped_column(String(64), default="")
    part_b_proper_operation_statement: Mapped[str] = mapped_column(Text, default="")

    status: Mapped[CertificateStatus] = mapped_column(Enum(CertificateStatus), default=CertificateStatus.PENDING_APPROVAL)
    pdf_storage_path: Mapped[str] = mapped_column(String(512), default="")

    generated_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    approved_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
