from pydantic import BaseModel


class HolisticReportOutput(BaseModel):
    """Strict output_type for the Reporting Agent's final, court-facing report. The Agents
    SDK enforces this shape on every run; report_integrity_guardrail additionally checks
    that every certificate_id referenced actually exists (catches hallucinated citations)."""

    case_id: str
    executive_summary: str
    key_findings: list[str]
    certificate_ids: list[str]
    cross_reference_alerts: list[str]
    recommended_next_steps: list[str]
