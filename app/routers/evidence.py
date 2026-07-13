import shutil
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.config import get_settings
from app.database import get_db
from app.models.evidence import ChainOfCustodyEvent, Evidence, EvidenceType
from app.models.user import Role, User
from app.schemas.evidence import ChainOfCustodyEventOut, EvidenceOut
from app.services.audit_service import log_access
from app.services.case_access import assert_case_jurisdiction, get_case_or_404
from app.services.hashing import hash_file

router = APIRouter(prefix="/evidence", tags=["evidence"])
settings = get_settings()


@router.post("", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    case_id: str = Form(...),
    evidence_type: EvidenceType = Form(...),
    device_model: str = Form(""),
    device_imei: str = Form(""),
    device_os: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.OFFICER, Role.FORENSIC_SCIENTIST, Role.ADMIN)),
):
    case = await get_case_or_404(db, case_id)
    assert_case_jurisdiction(current_user, case)

    case_dir = settings.evidence_storage_path / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4()}_{file.filename}"
    dest_path = case_dir / stored_name
    with dest_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    sha256_hex, md5_hex = hash_file(dest_path)

    evidence = Evidence(
        case_id=case_id,
        evidence_type=evidence_type,
        original_filename=file.filename or stored_name,
        storage_path=str(dest_path),
        device_model=device_model,
        device_imei=device_imei,
        device_os=device_os,
        sha256_hash=sha256_hex,
        md5_hash=md5_hex,
        uploaded_by_id=current_user.id,
    )
    db.add(evidence)
    await db.flush()

    db.add(
        ChainOfCustodyEvent(
            evidence_id=evidence.id,
            actor_id=current_user.id,
            action="ingested",
            notes=f"Uploaded via FEMAS API, original filename '{file.filename}'",
            integrity_hash_at_event=sha256_hex,
        )
    )
    await db.commit()
    await db.refresh(evidence)
    await log_access(db, current_user, "upload_evidence", "evidence", evidence.id)
    return evidence


@router.get("/case/{case_id}", response_model=list[EvidenceOut])
async def list_evidence_for_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = await get_case_or_404(db, case_id)
    assert_case_jurisdiction(current_user, case)
    result = await db.execute(select(Evidence).where(Evidence.case_id == case_id))
    items = list(result.scalars().all())
    await log_access(db, current_user, "list_evidence", "case", case_id)
    return items


async def _get_evidence_or_404(db: AsyncSession, evidence_id: str) -> Evidence:
    evidence = await db.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return evidence


@router.get("/{evidence_id}", response_model=EvidenceOut)
async def get_evidence(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    evidence = await _get_evidence_or_404(db, evidence_id)
    case = await get_case_or_404(db, evidence.case_id)
    assert_case_jurisdiction(current_user, case)
    await log_access(db, current_user, "read_evidence", "evidence", evidence.id)
    return evidence


@router.get("/{evidence_id}/chain-of-custody", response_model=list[ChainOfCustodyEventOut])
async def get_chain_of_custody(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    evidence = await _get_evidence_or_404(db, evidence_id)
    case = await get_case_or_404(db, evidence.case_id)
    assert_case_jurisdiction(current_user, case)
    result = await db.execute(
        select(ChainOfCustodyEvent)
        .where(ChainOfCustodyEvent.evidence_id == evidence_id)
        .order_by(ChainOfCustodyEvent.occurred_at)
    )
    events = list(result.scalars().all())
    await log_access(db, current_user, "read_chain_of_custody", "evidence", evidence.id)
    return events
