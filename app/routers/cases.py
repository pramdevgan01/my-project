from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.case import Case
from app.models.user import Role, User
from app.schemas.case import CaseCreate, CaseOut
from app.services.audit_service import log_access
from app.services.case_access import assert_case_jurisdiction, get_case_or_404

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def create_case(
    payload: CaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.OFFICER, Role.ADMIN)),
):
    case = Case(
        fir_number=payload.fir_number,
        title=payload.title,
        description=payload.description,
        offense_sections=payload.offense_sections,
        jurisdiction=payload.jurisdiction,
        created_by_id=current_user.id,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    await log_access(db, current_user, "create_case", "case", case.id)
    return case


@router.get("", response_model=list[CaseOut])
async def list_cases(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Case)
    if current_user.role != Role.ADMIN:
        query = query.where(Case.jurisdiction == current_user.jurisdiction)
    result = await db.execute(query.order_by(Case.created_at.desc()))
    cases = list(result.scalars().all())
    await log_access(db, current_user, "list_cases", "case", purpose="case triage/listing")
    return cases


@router.get("/{case_id}", response_model=CaseOut)
async def get_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = await get_case_or_404(db, case_id)
    assert_case_jurisdiction(current_user, case)
    await log_access(db, current_user, "read_case", "case", case.id)
    return case
