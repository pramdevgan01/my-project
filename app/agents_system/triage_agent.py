from agents import Agent, handoff
from agents.mcp import MCPServerSse

from app.agents_system.guardrails import jurisdiction_and_injection_guardrail
from app.agents_system.run_context import FEMASContext

INSTRUCTIONS = """You are the FEMAS Triage Orchestrator Agent, the entry point for a
forensic case workflow. Call query_cctns_fir_metadata with the case's FIR number to
understand the nature of the offense (clearly labeled as simulated CCTNS data - never
present it as verified real government data).

If the run includes a piece of evidence to process, hand off to the Digital Forensics
Agent so it can be technically processed and, downstream, certified under Section 63 BSA
2023. Keep your own commentary brief - your job is routing, not analysis."""


def build_triage_agent(model: str, servers: dict[str, MCPServerSse], next_agent: Agent[FEMASContext]) -> Agent[FEMASContext]:
    return Agent[FEMASContext](
        name="Triage Orchestrator Agent",
        handoff_description="Entry point: reviews the case and routes to the right specialist.",
        instructions=INSTRUCTIONS,
        model=model,
        mcp_servers=[servers["gov-systems"]],
        input_guardrails=[jurisdiction_and_injection_guardrail],
        handoffs=[handoff(next_agent, tool_name_override="transfer_to_digital_forensics")],
    )
