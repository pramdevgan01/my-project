from agents import Agent
from agents.mcp import MCPServerSse

from app.agents_system.guardrails import report_integrity_guardrail
from app.agents_system.output_types import HolisticReportOutput
from app.agents_system.run_context import FEMASContext

INSTRUCTIONS = """You are the FEMAS Reporting Agent, the final stage of the forensic
evidence pipeline. You synthesize everything produced earlier in this run - device
analysis findings, malware scan results, and the Section 63 BSA certificate that Legal
Compliance drafted - into one structured, court-ready holistic report.

Use fetch_icjs_suspect_dossier when a suspect name is mentioned, to cross-reference prior
cases and flag habitual offenders (clearly labeled as simulated ICJS data - never present
it as verified real government data).

certificate_ids must list only certificate ids that were actually produced earlier in
this conversation by the Legal Compliance Agent - never invent one. Base key_findings and
cross_reference_alerts strictly on what tools actually returned earlier in this run. If
nothing relevant was found, say so plainly rather than fabricating detail."""


def build_reporting_agent(model: str, servers: dict[str, MCPServerSse]) -> Agent[FEMASContext]:
    return Agent[FEMASContext](
        name="Reporting Agent",
        handoff_description="Synthesizes all prior findings into the final holistic case report.",
        instructions=INSTRUCTIONS,
        model=model,
        mcp_servers=[servers["gov-systems"]],
        output_type=HolisticReportOutput,
        output_guardrails=[report_integrity_guardrail],
    )
