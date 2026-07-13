"""SIMULATED integrations for CCTNS / ICJS / NDSO.

FEMAS has no real network access to India's Crime and Criminal Tracking Network and
Systems (CCTNS), the Inter-operable Criminal Justice System (ICJS), or the National
Database on Sexual Offenders (NDSO). These tools return deterministic, clearly-labeled
fixture data shaped like what those systems would return, so the tool *interface* is
correct and swappable for a real state-DB-backed FastMCP server later (per the report's
architecture, each state would run its own lightweight MCP server next to its existing
CCTNS/ICJS database).
"""

import hashlib
from datetime import datetime, timedelta, timezone

from mcp.server.fastmcp import FastMCP

gov_systems_mcp = FastMCP("femas-gov-systems", stateless_http=True)

_OFFENSE_SECTIONS = ["IPC 420", "BNS 111", "BNS 303", "NDPS 21", "BNS 66"]
_STATIONS = ["PS Connaught Place", "PS Bandra", "PS MG Road", "PS Salt Lake", "PS Anna Nagar"]


def _seed(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest(), 16)


@gov_systems_mcp.tool()
def query_cctns_fir_metadata(fir_number: str) -> dict:
    """[SIMULATED CCTNS DATA] Look up First Information Report metadata by FIR number."""
    seed = _seed(fir_number)
    filed_on = datetime.now(timezone.utc) - timedelta(days=seed % 120)
    return {
        "source": "SIMULATED_CCTNS_MOCK",
        "fir_number": fir_number,
        "police_station": _STATIONS[seed % len(_STATIONS)],
        "offense_sections": [_OFFENSE_SECTIONS[(seed + i) % len(_OFFENSE_SECTIONS)] for i in range(2)],
        "investigating_officer": f"SI {['R. Sharma', 'A. Iyer', 'P. Singh', 'M. Nair'][seed % 4]}",
        "filed_on": filed_on.date().isoformat(),
        "status": ["under_investigation", "chargesheet_filed", "pending_forensic_report"][seed % 3],
    }


@gov_systems_mcp.tool()
def fetch_icjs_suspect_dossier(suspect_name: str) -> dict:
    """[SIMULATED ICJS DATA] Cross-reference a suspect name across the Inter-operable
    Criminal Justice System pillars (police, courts, prisons, prosecution)."""
    seed = _seed(suspect_name)
    prior_cases = seed % 4
    return {
        "source": "SIMULATED_ICJS_MOCK",
        "suspect_name": suspect_name,
        "prior_case_count": prior_cases,
        "prior_case_fir_numbers": [f"FIR/{(seed + i) % 9999:04d}/2024" for i in range(prior_cases)],
        "known_aliases": [] if seed % 5 else [f"alias_{seed % 100}"],
        "risk_flag": "habitual_offender" if prior_cases >= 3 else "no_flag",
    }


@gov_systems_mcp.tool()
def fetch_ndso_dna_match(dna_profile_id: str) -> dict:
    """[SIMULATED NDSO DATA] Cross-reference an extracted DNA profile against the National
    Database on Sexual Offenders."""
    seed = _seed(dna_profile_id)
    matched = seed % 7 == 0
    return {
        "source": "SIMULATED_NDSO_MOCK",
        "dna_profile_id": dna_profile_id,
        "match_found": matched,
        "match_confidence_percent": (85 + seed % 15) if matched else 0,
        "matched_offender_registry_id": f"NDSO-{seed % 99999:05d}" if matched else None,
    }
