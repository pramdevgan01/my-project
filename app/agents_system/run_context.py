from dataclasses import dataclass

from app.models.user import Role


@dataclass
class FEMASContext:
    """Passed to Runner.run() as the shared context object. Available to every tool,
    guardrail, and handoff input_filter in the run via RunContextWrapper.context — this is
    what the RBAC tool_filter and the jurisdiction input guardrail read from."""

    run_id: str
    case_id: str
    evidence_id: str | None
    user_id: str
    user_role: Role
    user_jurisdiction: str
    case_jurisdiction: str
