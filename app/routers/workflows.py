from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents_system.orchestrator import run_forensic_workflow
from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.evidence import Evidence
from app.models.user import Role, User
from app.models.workflow import WorkflowRun
from app.schemas.workflow import WorkflowRunOut, WorkflowRunRequest
from app.services.audit_service import log_access
from app.services.case_access import assert_case_jurisdiction, get_case_or_404

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/run", response_model=WorkflowRunOut, status_code=status.HTTP_201_CREATED)
async def start_workflow(
    payload: WorkflowRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.OFFICER, Role.FORENSIC_SCIENTIST, Role.ADMIN)),
):
    case = await get_case_or_404(db, payload.case_id)
    assert_case_jurisdiction(current_user, case)

    evidence = None
    if payload.evidence_id:
        evidence = await db.get(Evidence, payload.evidence_id)
        if evidence is None or evidence.case_id != case.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found for this case")

    await log_access(db, current_user, "start_workflow", "case", case.id, purpose="agent pipeline execution")

    run = await run_forensic_workflow(
        db,
        case=case,
        evidence=evidence,
        user=current_user,
        instruction=payload.instruction,
    )
    result = await db.execute(
        select(WorkflowRun).options(selectinload(WorkflowRun.steps)).where(WorkflowRun.id == run.id)
    )
    return result.scalar_one()


@router.get("/{run_id}", response_model=WorkflowRunOut)
async def get_workflow_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WorkflowRun).options(selectinload(WorkflowRun.steps)).where(WorkflowRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run not found")

    case = await get_case_or_404(db, run.case_id)
    assert_case_jurisdiction(current_user, case)
    return run


@router.get("", response_model=list[WorkflowRunOut])
async def list_workflow_runs(
    case_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(WorkflowRun).options(selectinload(WorkflowRun.steps))
    if case_id:
        query = query.where(WorkflowRun.case_id == case_id)
    result = await db.execute(query.order_by(WorkflowRun.started_at.desc()))
    return list(result.scalars().all())
