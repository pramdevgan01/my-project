from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User


async def log_access(
    db: AsyncSession,
    actor: User,
    action: str,
    resource_type: str,
    resource_id: str = "",
    purpose: str = "criminal investigation",
    detail: str = "",
    commit: bool = True,
) -> AuditLog:
    """Record a DPDPA-oriented access log entry (purpose-limitation trail).

    Every read/write of case, evidence, or certificate data is expected to call this
    so that access is always attributable to an actor and a stated purpose.
    """
    entry = AuditLog(
        actor_id=actor.id,
        actor_role=actor.role.value,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        purpose=purpose,
        detail=detail,
    )
    db.add(entry)
    if commit:
        await db.commit()
    return entry
