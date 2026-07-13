import re

from agents import GuardrailFunctionOutput, RunContextWrapper, input_guardrail, output_guardrail
from agents.agent import AgentBase

from app.agents_system.output_types import HolisticReportOutput
from app.agents_system.run_context import FEMASContext
from app.database import async_session_maker
from app.models.certificate import BSACertificate
from app.models.user import Role

_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore (all|any|previous|prior) instructions",
        r"reveal (the |your )?system prompt",
        r"you are now (in )?(dan|jailbreak|developer mode)",
        r"disregard (the |your )?(above|previous) (rules|instructions)",
        r"act as (an? )?unrestricted",
    ]
]


@input_guardrail
async def jurisdiction_and_injection_guardrail(
    ctx: RunContextWrapper[FEMASContext],
    agent: AgentBase,
    agent_input: str | list,
) -> GuardrailFunctionOutput:
    """Blocks a run before any agent executes if:
    (a) the requesting officer's jurisdiction does not match the case's jurisdiction
        (unless they are ADMIN) - the report's "officer queries a case file outside
        their territorial jurisdiction" example, or
    (b) the free-text input looks like a prompt-injection attempt against the pipeline.
    """
    context = ctx.context
    if context.user_role != Role.ADMIN and context.user_jurisdiction != context.case_jurisdiction:
        return GuardrailFunctionOutput(
            output_info={
                "reason": "jurisdiction_mismatch",
                "user_jurisdiction": context.user_jurisdiction,
                "case_jurisdiction": context.case_jurisdiction,
            },
            tripwire_triggered=True,
        )

    text = agent_input if isinstance(agent_input, str) else str(agent_input)
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return GuardrailFunctionOutput(
                output_info={"reason": "suspected_prompt_injection", "matched_pattern": pattern.pattern},
                tripwire_triggered=True,
            )

    return GuardrailFunctionOutput(output_info={"reason": "ok"}, tripwire_triggered=False)


@output_guardrail
async def report_integrity_guardrail(
    ctx: RunContextWrapper[FEMASContext],
    agent: AgentBase,
    agent_output: HolisticReportOutput,
) -> GuardrailFunctionOutput:
    """Beyond the Pydantic output_type shape, verify every certificate_id the Reporting
    Agent cited actually exists in the database and belongs to this case - catching a
    hallucinated citation before it reaches a human, mirroring the report's concern about
    a malformed/fabricated legal output reaching the record."""
    if not agent_output.certificate_ids:
        return GuardrailFunctionOutput(output_info={"reason": "ok_no_certificates_cited"}, tripwire_triggered=False)

    async with async_session_maker() as db:
        for certificate_id in agent_output.certificate_ids:
            certificate = await db.get(BSACertificate, certificate_id)
            if certificate is None or certificate.case_id != ctx.context.case_id:
                return GuardrailFunctionOutput(
                    output_info={
                        "reason": "hallucinated_or_foreign_certificate_id",
                        "certificate_id": certificate_id,
                    },
                    tripwire_triggered=True,
                )

    return GuardrailFunctionOutput(output_info={"reason": "ok"}, tripwire_triggered=False)
