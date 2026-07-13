from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.certificate import BSACertificate, CertificateStatus
from app.models.user import Role, User
from app.schemas.certificate import CertificateOut
from app.services.audit_service import log_access
from app.services.case_access import assert_case_jurisdiction, get_case_or_404

router = APIRouter(prefix="/certificates", tags=["certificates"])


async def _get_certificate_or_404(db: AsyncSession, certificate_id: str) -> BSACertificate:
    certificate = await db.get(BSACertificate, certificate_id)
    if certificate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    return certificate


@router.get("", response_model=list[CertificateOut])
async def list_certificates(
    case_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(BSACertificate)
    if case_id:
        query = query.where(BSACertificate.case_id == case_id)
    result = await db.execute(query.order_by(BSACertificate.generated_at.desc()))
    certificates = list(result.scalars().all())
    await log_access(db, current_user, "list_certificates", "certificate", purpose="BSA compliance review")
    return certificates


@router.get("/{certificate_id}", response_model=CertificateOut)
async def get_certificate(
    certificate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    certificate = await _get_certificate_or_404(db, certificate_id)
    case = await get_case_or_404(db, certificate.case_id)
    assert_case_jurisdiction(current_user, case)
    await log_access(db, current_user, "read_certificate", "certificate", certificate.id)
    return certificate


@router.get("/{certificate_id}/download")
async def download_certificate(
    certificate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    certificate = await _get_certificate_or_404(db, certificate_id)
    case = await get_case_or_404(db, certificate.case_id)
    assert_case_jurisdiction(current_user, case)
    if not certificate.pdf_storage_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Certificate PDF has not been rendered yet")
    await log_access(db, current_user, "download_certificate", "certificate", certificate.id)
    return FileResponse(
        certificate.pdf_storage_path,
        media_type="application/pdf",
        filename=f"BSA_Section63_Certificate_{certificate.id}.pdf",
    )


@router.post("/{certificate_id}/approve", response_model=CertificateOut)
async def approve_certificate(
    certificate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.NODAL_OFFICER, Role.ADMIN)),
):
    """Human-in-the-loop sign-off: the AI-drafted certificate becomes court-final only
    once an authorized nodal officer approves it here."""
    certificate = await _get_certificate_or_404(db, certificate_id)
    if certificate.status != CertificateStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Certificate is not pending approval (current status: {certificate.status.value})",
        )
    certificate.status = CertificateStatus.APPROVED
    certificate.approved_by_id = current_user.id
    certificate.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(certificate)
    await log_access(
        db, current_user, "approve_certificate", "certificate", certificate.id,
        purpose="Section 63(4) BSA nodal officer sign-off",
    )
    return certificate


@router.post("/{certificate_id}/reject", response_model=CertificateOut)
async def reject_certificate(
    certificate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.NODAL_OFFICER, Role.ADMIN)),
):
    certificate = await _get_certificate_or_404(db, certificate_id)
    if certificate.status != CertificateStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Certificate is not pending approval (current status: {certificate.status.value})",
        )
    certificate.status = CertificateStatus.REJECTED
    certificate.approved_by_id = current_user.id
    certificate.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(certificate)
    await log_access(db, current_user, "reject_certificate", "certificate", certificate.id)
    return certificate
