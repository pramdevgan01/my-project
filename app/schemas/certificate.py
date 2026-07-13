from datetime import datetime

from pydantic import BaseModel

from app.models.certificate import CertificateStatus


class CertificateOut(BaseModel):
    id: str
    evidence_id: str
    case_id: str
    part_a_declarant_name: str
    part_a_device_particulars: str
    part_a_lawful_control_statement: str
    part_b_expert_name: str
    part_b_hash_algorithm: str
    part_b_hash_value: str
    part_b_proper_operation_statement: str
    status: CertificateStatus
    generated_by_id: str
    approved_by_id: str | None
    generated_at: datetime
    approved_at: datetime | None

    model_config = {"from_attributes": True}
