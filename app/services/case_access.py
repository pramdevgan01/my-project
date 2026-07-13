from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.user import Role, User


async def get_case_or_404(db: AsyncSession, case_id: str) -> Case:
    case = await db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


def assert_case_jurisdiction(current_user: User, case: Case) -> None:
    if current_user.role != Role.ADMIN and current_user.jurisdiction != case.jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Case falls outside your jurisdiction",
        )
