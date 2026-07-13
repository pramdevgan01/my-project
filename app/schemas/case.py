from datetime import datetime

from pydantic import BaseModel

from app.models.case import CaseStatus


class CaseCreate(BaseModel):
    fir_number: str
    title: str
    description: str = ""
    offense_sections: str = ""
    jurisdiction: str


class CaseOut(BaseModel):
    id: str
    fir_number: str
    title: str
    description: str
    offense_sections: str
    jurisdiction: str
    status: CaseStatus
    created_by_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
