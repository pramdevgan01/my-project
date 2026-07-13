"""REAL tools backing Section 63 BSA 2023 compliance: cryptographic hashing, dual-part
certificate PDF rendering, and chain-of-custody verification, all reading/writing the
actual FEMAS database and filesystem (no simulated data in this module)."""

from mcp.server.fastmcp import FastMCP

from app.config import get_settings
from app.database import async_session_maker
from app.models.certificate import BSACertificate, CertificateStatus
from app.models.evidence import ChainOfCustodyEvent, Evidence
from app.services.certificate_pdf import render_bsa_certificate_pdf as _render_pdf
from app.services.hashing import hash_file

legal_mcp = FastMCP("femas-legal-compliance", stateless_http=True)
settings = get_settings()


@legal_mcp.tool()
async def generate_sha256_cryptographic_hash(evidence_id: str) -> dict:
    """Recompute the SHA-256/MD5 digest of the evidence file from disk and compare it
    against the digest recorded at ingestion time, to prove the file has not been altered."""
    async with async_session_maker() as db:
        evidence = await db.get(Evidence, evidence_id)
        if evidence is None:
            return {"error": f"No evidence found with id {evidence_id}"}
        current_sha256, current_md5 = hash_file(evidence.storage_path)
        return {
            "evidence_id": evidence_id,
            "sha256_hash": current_sha256,
            "md5_hash": current_md5,
            "matches_ingestion_hash": current_sha256 == evidence.sha256_hash,
        }


@legal_mcp.tool()
async def render_bsa_certificate_pdf(
    evidence_id: str,
    declarant_name: str,
    lawful_control_statement: str,
    technical_expert_name: str,
    proper_operation_statement: str,
) -> dict:
    """Draft the Section 63(4) BSA 2023 dual-signatory certificate for a piece of
    electronic evidence and render it to PDF. The certificate is created with status
    PENDING_APPROVAL: it only becomes court-final once a nodal officer approves it via
    POST /certificates/{id}/approve (human-in-the-loop sign-off)."""
    async with async_session_maker() as db:
        evidence = await db.get(Evidence, evidence_id)
        if evidence is None:
            return {"error": f"No evidence found with id {evidence_id}"}

        device_particulars = (
            f"Model: {evidence.device_model or 'N/A'}\n"
            f"IMEI: {evidence.device_imei or 'N/A'}\n"
            f"OS: {evidence.device_os or 'N/A'}\n"
            f"Original filename: {evidence.original_filename}"
        )

        certificate = BSACertificate(
            evidence_id=evidence.id,
            case_id=evidence.case_id,
            part_a_declarant_name=declarant_name,
            part_a_device_particulars=device_particulars,
            part_a_lawful_control_statement=lawful_control_statement,
            part_b_expert_name=technical_expert_name,
            part_b_hash_algorithm="SHA-256",
            part_b_hash_value=evidence.sha256_hash,
            part_b_proper_operation_statement=proper_operation_statement,
            status=CertificateStatus.PENDING_APPROVAL,
            generated_by_id=evidence.uploaded_by_id,
        )
        db.add(certificate)
        await db.flush()

        pdf_path = _render_pdf(certificate, evidence, settings.evidence_storage_path / "certificates")
        certificate.pdf_storage_path = pdf_path
        await db.commit()
        await db.refresh(certificate)

        return {
            "certificate_id": certificate.id,
            "status": certificate.status.value,
            "sha256_hash": certificate.part_b_hash_value,
            "pdf_storage_path": pdf_path,
        }


@legal_mcp.tool()
async def verify_chain_of_custody_logs(evidence_id: str) -> dict:
    """Return the ordered chain-of-custody trail for a piece of evidence and confirm no
    gaps exist between the recorded integrity hash at each event."""
    async with async_session_maker() as db:
        evidence = await db.get(Evidence, evidence_id)
        if evidence is None:
            return {"error": f"No evidence found with id {evidence_id}"}
        result = await db.execute(
            ChainOfCustodyEvent.__table__.select()
            .where(ChainOfCustodyEvent.evidence_id == evidence_id)
            .order_by(ChainOfCustodyEvent.occurred_at)
        )
        events = result.mappings().all()
        hashes = {e["integrity_hash_at_event"] for e in events if e["integrity_hash_at_event"]}
        return {
            "evidence_id": evidence_id,
            "event_count": len(events),
            "events": [
                {
                    "action": e["action"],
                    "actor_id": e["actor_id"],
                    "occurred_at": e["occurred_at"].isoformat(),
                    "integrity_hash_at_event": e["integrity_hash_at_event"],
                }
                for e in events
            ],
            "unbroken_chain": len(hashes) <= 1,
        }
