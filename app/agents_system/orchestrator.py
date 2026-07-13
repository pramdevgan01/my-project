from contextlib import AsyncExitStack
from datetime import datetime, timezone

from agents import (
    InputGuardrailTripwireTriggered,
    ModelBehaviorError,
    OutputGuardrailTripwireTriggered,
    Runner,
)
from agents.mcp import MCPServerSse, ToolFilterContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.digital_forensics_agent import build_digital_forensics_agent
from app.agents_system.legal_compliance_agent import build_legal_compliance_agent
from app.agents_system.reporting_agent import build_reporting_agent
from app.agents_system.run_context import FEMASContext
from app.agents_system.triage_agent import build_triage_agent
from app.auth.security import create_access_token
from app.config import get_settings
from app.mcp_servers.access_policy import tool_allowed_for_role
from app.models.case import Case
from app.models.evidence import Evidence
from app.models.user import User
from app.models.workflow import WorkflowRun, WorkflowStatus, WorkflowStep

settings = get_settings()

_MCP_KEYS = ("legal", "forensics", "gov-systems")


def _tool_filter(filter_context: ToolFilterContext, tool) -> bool:
    """The Enterprise MCP Gateway's identity-aware filter: masks tools the requesting
    user's role is not permitted to see before the model ever learns they exist."""
    context: FEMASContext = filter_context.run_context.context
    return tool_allowed_for_role(tool.name, context.user_role)


async def _connect_mcp_servers(stack: AsyncExitStack, user: User) -> dict[str, MCPServerSse]:
    token = create_access_token(subject=user.username, role=user.role.value, jurisdiction=user.jurisdiction)
    headers = {"Authorization": f"Bearer {token}"}

    servers: dict[str, MCPServerSse] = {}
    for key in _MCP_KEYS:
        server = MCPServerSse(
            params={"url": f"{settings.mcp_base_url}/mcp/{key}/sse", "headers": headers},
            name=f"femas-{key}",
            tool_filter=_tool_filter,
            client_session_timeout_seconds=30,
        )
        await stack.enter_async_context(server)
        servers[key] = server
    return servers


async def run_forensic_workflow(
    db: AsyncSession,
    *,
    case: Case,
    evidence: Evidence | None,
    user: User,
    instruction: str,
) -> WorkflowRun:
    """Runs Triage -> Digital Forensics -> Legal Compliance -> Reporting for a case,
    persisting a hierarchical WorkflowRun/WorkflowStep trace (this app's stand-in for the
    report's Laminar tracing integration)."""
    run = WorkflowRun(
        case_id=case.id,
        evidence_id=evidence.id if evidence else None,
        initiated_by_id=user.id,
        status=WorkflowStatus.RUNNING,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    context = FEMASContext(
        run_id=run.id,
        case_id=case.id,
        evidence_id=evidence.id if evidence else None,
        user_id=user.id,
        user_role=user.role,
        user_jurisdiction=user.jurisdiction,
        case_jurisdiction=case.jurisdiction,
    )

    sequence = 0

    async def _log_step(step_type: str, agent_name: str, detail: str) -> None:
        nonlocal sequence
        sequence += 1
        db.add(
            WorkflowStep(
                run_id=run.id,
                sequence=sequence,
                step_type=step_type,
                agent_name=agent_name,
                detail=detail[:4000],
            )
        )
        await db.commit()

    try:
        async with AsyncExitStack() as stack:
            servers = await _connect_mcp_servers(stack, user)

            model = settings.agents_model
            reporting_agent = build_reporting_agent(model, servers)
            legal_compliance_agent = build_legal_compliance_agent(model, servers, reporting_agent)
            digital_forensics_agent = build_digital_forensics_agent(model, servers, legal_compliance_agent)
            triage_agent = build_triage_agent(model, servers, digital_forensics_agent)

            prompt = (
                f"{instruction}\n\n"
                f"Case ID: {case.id}\nFIR number: {case.fir_number}\nJurisdiction: {case.jurisdiction}\n"
                + (f"Evidence ID to process: {evidence.id} ({evidence.evidence_type.value})" if evidence else "No evidence attached to this run.")
            )

            result = await Runner.run(triage_agent, prompt, context=context, max_turns=20)

            for item in result.new_items:
                item_type = getattr(item, "type", "unknown")
                agent_name = getattr(getattr(item, "agent", None), "name", "")
                if item_type == "tool_call_item":
                    await _log_step("tool_call", agent_name, f"called {getattr(item, 'tool_name', 'unknown_tool')}")
                elif item_type == "tool_call_output_item":
                    await _log_step("tool_call", agent_name, f"tool output: {item.output}")
                elif item_type == "handoff_output_item":
                    source = getattr(item.source_agent, "name", "?")
                    target = getattr(item.target_agent, "name", "?")
                    await _log_step("handoff", agent_name, f"{source} -> {target}")
                elif item_type == "message_output_item":
                    await _log_step("agent_turn", agent_name, str(item.raw_item))

            run.status = WorkflowStatus.COMPLETED
            run.final_output = (
                result.final_output.model_dump_json()
                if hasattr(result.final_output, "model_dump_json")
                else str(result.final_output)
            )

    except InputGuardrailTripwireTriggered as exc:
        run.status = WorkflowStatus.BLOCKED_BY_GUARDRAIL
        run.error_message = f"Input guardrail blocked this run: {exc}"
        await _log_step("guardrail", "input_guardrail", run.error_message)
    except OutputGuardrailTripwireTriggered as exc:
        run.status = WorkflowStatus.BLOCKED_BY_GUARDRAIL
        run.error_message = f"Output guardrail blocked this run: {exc}"
        await _log_step("guardrail", "output_guardrail", run.error_message)
    except ModelBehaviorError as exc:
        run.status = WorkflowStatus.FAILED
        run.error_message = f"Model produced output that did not conform to the required schema: {exc}"
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller via WorkflowRun.error_message
        run.status = WorkflowStatus.FAILED
        run.error_message = f"{type(exc).__name__}: {exc}"

    run.finished_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(run)
    return run
