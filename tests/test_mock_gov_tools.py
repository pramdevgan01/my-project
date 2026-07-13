import json

from app.mcp_servers.forensics_tools import forensics_mcp
from app.mcp_servers.gov_systems_tools import gov_systems_mcp
from app.mcp_servers.legal_tools import legal_mcp
from app.models.evidence import Evidence, EvidenceType


async def _call(server, name, args):
    result = await server.call_tool(name, args)
    # FastMCP.call_tool returns a sequence of ContentBlocks (text) for simple dict returns.
    text = result[0].text if isinstance(result, (list, tuple)) else result
    return json.loads(text) if isinstance(text, str) else text


async def test_query_cctns_fir_metadata_is_labeled_simulated():
    data = await _call(gov_systems_mcp, "query_cctns_fir_metadata", {"fir_number": "FIR/0042/2026"})
    assert data["source"] == "SIMULATED_CCTNS_MOCK"
    assert data["fir_number"] == "FIR/0042/2026"
    assert "police_station" in data


async def test_query_cctns_is_deterministic_for_same_input():
    first = await _call(gov_systems_mcp, "query_cctns_fir_metadata", {"fir_number": "FIR/9999/2026"})
    second = await _call(gov_systems_mcp, "query_cctns_fir_metadata", {"fir_number": "FIR/9999/2026"})
    assert first == second


async def test_fetch_icjs_suspect_dossier_is_labeled_simulated():
    data = await _call(gov_systems_mcp, "fetch_icjs_suspect_dossier", {"suspect_name": "John Doe"})
    assert data["source"] == "SIMULATED_ICJS_MOCK"
    assert "risk_flag" in data


async def test_forensics_tools_report_missing_evidence(db_session):
    data = await _call(forensics_mcp, "extract_exif_data", {"evidence_id": "does-not-exist"})
    assert data["source"] == "SIMULATED_EXIF_MOCK"
    assert "error" in data


async def test_forensics_tools_use_real_evidence_record(db_session):
    evidence = Evidence(
        id="ev-forensics-1",
        case_id="case-1",
        evidence_type=EvidenceType.MOBILE_EXTRACTION,
        original_filename="dump.bin",
        storage_path="/tmp/does-not-matter",
        device_model="OnePlus 11",
        sha256_hash="c" * 64,
        md5_hash="d" * 32,
        uploaded_by_id="user-1",
    )
    db_session.add(evidence)
    await db_session.commit()

    data = await _call(forensics_mcp, "parse_mobile_file_system", {"evidence_id": "ev-forensics-1"})
    assert data["source"] == "SIMULATED_MOBILE_FS_MOCK"
    assert "artifacts_recovered" in data
    assert "error" not in data


async def test_legal_tools_reports_missing_evidence(db_session):
    data = await _call(legal_mcp, "generate_sha256_cryptographic_hash", {"evidence_id": "does-not-exist"})
    assert "error" in data
