from datetime import datetime

from pydantic import BaseModel

from app.models.evidence import EvidenceType


class EvidenceOut(BaseModel):
    id: str
    case_id: str
    evidence_type: EvidenceType
    original_filename: str
    device_model: str
    device_imei: str
    device_os: str
    sha256_hash: str
    md5_hash: str
    uploaded_by_id: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ChainOfCustodyEventOut(BaseModel):
    id: str
    evidence_id: str
    actor_id: str
    action: str
    notes: str
    integrity_hash_at_event: str
    occurred_at: datetime

    model_config = {"from_attributes": True}
