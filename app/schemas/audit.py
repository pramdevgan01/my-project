from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    actor_id: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str
    purpose: str
    detail: str
    occurred_at: datetime

    model_config = {"from_attributes": True}
