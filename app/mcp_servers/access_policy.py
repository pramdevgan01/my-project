from app.models.user import Role

# Which roles may see/invoke each MCP tool. This is the single source of truth consulted
# both by the Agents SDK client's per-agent tool_filter (masking tools the model never even
# sees - the report's "identity-aware Gateway") and, defense-in-depth, inside each tool
# implementation itself before it touches data.
TOOL_ROLE_REQUIREMENTS: dict[str, set[Role]] = {
    # gov_systems_tools.py (simulated CCTNS/ICJS/NDSO)
    "query_cctns_fir_metadata": {Role.OFFICER, Role.FORENSIC_SCIENTIST, Role.NODAL_OFFICER, Role.ADMIN},
    "fetch_icjs_suspect_dossier": {Role.OFFICER, Role.NODAL_OFFICER, Role.ADMIN},
    "fetch_ndso_dna_match": {Role.FORENSIC_SCIENTIST, Role.NODAL_OFFICER, Role.ADMIN},
    # forensics_tools.py (simulated device analysis)
    "extract_exif_data": {Role.FORENSIC_SCIENTIST, Role.ADMIN},
    "run_isolated_malware_scan": {Role.FORENSIC_SCIENTIST, Role.ADMIN},
    "parse_mobile_file_system": {Role.FORENSIC_SCIENTIST, Role.ADMIN},
    # legal_tools.py (real hashing / PDF / chain-of-custody)
    "generate_sha256_cryptographic_hash": {Role.FORENSIC_SCIENTIST, Role.NODAL_OFFICER, Role.ADMIN},
    "render_bsa_certificate_pdf": {Role.FORENSIC_SCIENTIST, Role.NODAL_OFFICER, Role.ADMIN},
    "verify_chain_of_custody_logs": {Role.FORENSIC_SCIENTIST, Role.NODAL_OFFICER, Role.ADMIN},
}


# Tools whose invocation requires an asynchronous human-in-the-loop sign-off by a senior
# examiner (nodal officer / admin) before the gateway will execute them, on top of the
# role gate above. NDSO queries touch an especially sensitive registry (DPDPA "sensitive
# personal data"), so a valid role alone is not sufficient.
SENSITIVE_TOOLS_REQUIRING_APPROVAL: set[str] = {
    "fetch_ndso_dna_match",
}


def tool_allowed_for_role(tool_name: str, role: Role) -> bool:
    allowed = TOOL_ROLE_REQUIREMENTS.get(tool_name)
    return True if allowed is None else role in allowed


def tool_requires_approval(tool_name: str) -> bool:
    return tool_name in SENSITIVE_TOOLS_REQUIRING_APPROVAL
