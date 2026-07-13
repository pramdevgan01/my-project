from datetime import datetime

from pydantic import BaseModel

from app.models.workflow import WorkflowStatus


class WorkflowRunRequest(BaseModel):
    case_id: str
    evidence_id: str | None = None
    instruction: str = "Process the submitted evidence for this case end to end."


class WorkflowStepOut(BaseModel):
    id: str
    sequence: int
    step_type: str
    agent_name: str
    detail: str
    occurred_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRunOut(BaseModel):
    id: str
    case_id: str
    evidence_id: str | None
    initiated_by_id: str
    status: WorkflowStatus
    final_output: str
    error_message: str
    started_at: datetime
    finished_at: datetime | None
    steps: list[WorkflowStepOut] = []

    model_config = {"from_attributes": True}
