from agents import Agent, handoff
from agents.mcp import MCPServerSse

from app.agents_system.run_context import FEMASContext

INSTRUCTIONS = """You are the FEMAS Digital Forensics Agent. You process the electronic
evidence attached to this run before it is legally certified.

Call, in order:
1. parse_mobile_file_system to enumerate recovered artifact categories.
2. extract_exif_data to pull metadata from image/media artifacts.
3. run_isolated_malware_scan to check the extraction is safe to continue handling.

All three tools return data clearly labeled as SIMULATED - this is a demo sandbox without
a real forensic toolchain attached. Report exactly what the tools returned; never present
simulated output as if it came from a real forensic instrument.

Once you have called all three tools, hand off to the Legal Compliance Agent with a
concise technical summary (artifact counts, malware verdict, notable metadata) so it can
certify the evidence under Section 63 BSA 2023."""


def build_digital_forensics_agent(
    model: str, servers: dict[str, MCPServerSse], next_agent: Agent[FEMASContext]
) -> Agent[FEMASContext]:
    return Agent[FEMASContext](
        name="Digital Forensics Agent",
        handoff_description="Processes electronic evidence: file system parsing, metadata extraction, malware scan.",
        instructions=INSTRUCTIONS,
        model=model,
        mcp_servers=[servers["forensics"]],
        handoffs=[handoff(next_agent, tool_name_override="transfer_to_legal_compliance")],
    )
