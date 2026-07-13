from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.database import get_db
from app.models.audit import AuditLog
from app.models.user import Role, User
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    resource_type: str | None = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role(Role.ADMIN)),
):
    query = select(AuditLog)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    query = query.order_by(AuditLog.occurred_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
