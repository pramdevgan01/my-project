"""SIMULATED digital forensics tooling.

FEMAS does not have a real EXIF parser, malware sandbox, or mobile filesystem extractor
wired up. These tools produce deterministic, clearly-labeled fixture output derived from
the real evidence record (looked up from the database by evidence_id) so the workflow is
exercised end-to-end; swap the tool bodies for real forensic tooling (ExifTool, Cuckoo
Sandbox, Cellebrite/Autopsy parsers, etc.) without changing the interface.
"""

import hashlib

from mcp.server.fastmcp import FastMCP

from app.database import async_session_maker
from app.models.evidence import Evidence

forensics_mcp = FastMCP("femas-forensics", stateless_http=True)


def _seed(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest(), 16)


async def _load_evidence(evidence_id: str) -> Evidence | None:
    async with async_session_maker() as db:
        return await db.get(Evidence, evidence_id)


@forensics_mcp.tool()
async def extract_exif_data(evidence_id: str) -> dict:
    """[SIMULATED] Extract EXIF/metadata from an image or media evidence item."""
    evidence = await _load_evidence(evidence_id)
    if evidence is None:
        return {"source": "SIMULATED_EXIF_MOCK", "error": f"No evidence found with id {evidence_id}"}
    seed = _seed(evidence.sha256_hash or evidence_id)
    return {
        "source": "SIMULATED_EXIF_MOCK",
        "evidence_id": evidence_id,
        "device_make": evidence.device_model.split(" ")[0] if evidence.device_model else "Unknown",
        "device_model": evidence.device_model or "Unknown",
        "gps_present": seed % 3 == 0,
        "gps_coordinates": f"{28 + seed % 5}.{seed % 9999:04d}N, {77 + seed % 5}.{(seed >> 4) % 9999:04d}E"
        if seed % 3 == 0
        else None,
        "created_timestamp_utc": None,
        "software_tag": ["Android Camera", "iOS Camera", "WhatsApp", "Unknown"][seed % 4],
    }


@forensics_mcp.tool()
async def run_isolated_malware_scan(evidence_id: str) -> dict:
    """[SIMULATED] Run the evidence file through an air-gapped malware sandbox."""
    evidence = await _load_evidence(evidence_id)
    if evidence is None:
        return {"source": "SIMULATED_SANDBOX_MOCK", "error": f"No evidence found with id {evidence_id}"}
    seed = _seed(evidence.sha256_hash or evidence_id)
    infected = seed % 11 == 0
    return {
        "source": "SIMULATED_SANDBOX_MOCK",
        "evidence_id": evidence_id,
        "sandbox_environment": "isolated-airgapped-vm",
        "sha256_scanned": evidence.sha256_hash,
        "malware_detected": infected,
        "signature_matches": [f"Trojan.Generic.{seed % 9999}"] if infected else [],
        "scan_verdict": "quarantine_recommended" if infected else "clean",
    }


@forensics_mcp.tool()
async def parse_mobile_file_system(evidence_id: str) -> dict:
    """[SIMULATED] Parse a mobile device extraction and enumerate recovered artifact categories."""
    evidence = await _load_evidence(evidence_id)
    if evidence is None:
        return {"source": "SIMULATED_MOBILE_FS_MOCK", "error": f"No evidence found with id {evidence_id}"}
    seed = _seed(evidence.sha256_hash or evidence_id)
    return {
        "source": "SIMULATED_MOBILE_FS_MOCK",
        "evidence_id": evidence_id,
        "artifacts_recovered": {
            "chat_exports": seed % 5,
            "call_logs": seed % 40,
            "media_files": seed % 200,
            "deleted_items_recovered": seed % 10,
        },
        "encryption_detected": seed % 2 == 0,
        "recommended_next_step": "route_to_legal_compliance_for_bsa_certification",
    }
