from agents import Agent, handoff
from agents.extensions.handoff_filters import remove_all_tools
from agents.mcp import MCPServerSse

from app.agents_system.run_context import FEMASContext

INSTRUCTIONS = """You are the FEMAS Legal Compliance Agent. Your sole job is ensuring
electronic evidence conforms to Section 63, Bharatiya Sakshya Adhiniyam (BSA) 2023, before
it can be relied on in court.

Steps, in order:
1. Call generate_sha256_cryptographic_hash on the evidence to confirm the file on disk
   still matches the hash recorded at ingestion (matches_ingestion_hash must be true). If
   it is false, stop and report the integrity failure instead of certifying anything.
2. Call verify_chain_of_custody_logs to confirm the custody trail is unbroken
   (unbroken_chain must be true) before proceeding.
3. Call render_bsa_certificate_pdf to draft the dual-part Section 63(4) certificate. Use
   'Investigating Officer' as declarant_name and 'FEMAS Digital Forensics Examiner' as
   technical_expert_name unless the conversation specifies real names. Write concise,
   factual lawful_control_statement and proper_operation_statement values.
4. The certificate this tool returns always has status 'pending_approval' - it requires a
   human nodal officer's sign-off before it is court-final. State this plainly; never
   claim a certificate is final or approved.
5. Once the certificate has been drafted (or the integrity check has failed and you have
   noted why), hand off to the Reporting Agent with a clear summary of what you found and
   the certificate_id, so it can be included in the final report."""


def build_legal_compliance_agent(
    model: str, servers: dict[str, MCPServerSse], next_agent: Agent[FEMASContext]
) -> Agent[FEMASContext]:
    return Agent[FEMASContext](
        name="Legal Compliance Agent",
        handoff_description="Certifies electronic evidence under Section 63 BSA 2023 via cryptographic hashing.",
        instructions=INSTRUCTIONS,
        model=model,
        mcp_servers=[servers["legal"]],
        handoffs=[
            handoff(
                next_agent,
                tool_name_override="transfer_to_reporting",
                input_filter=remove_all_tools,
            )
        ],
    )
