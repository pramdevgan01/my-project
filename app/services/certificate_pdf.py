from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF

from app.models.certificate import BSACertificate
from app.models.evidence import Evidence


def render_bsa_certificate_pdf(certificate: BSACertificate, evidence: Evidence, output_dir: Path) -> str:
    """Render the Section 63(4) BSA 2023 dual-signatory certificate schedule as a PDF.

    Returns the path the PDF was written to.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "CERTIFICATE UNDER SECTION 63(4), BHARATIYA SAKSHYA ADHINIYAM, 2023", align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        0, 6,
        f"Certificate ID: {certificate.id}\n"
        f"Case ID: {certificate.case_id}\n"
        f"Evidence ID: {certificate.evidence_id}\n"
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "PART A - Declaration by Person in Charge of the Device", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        0, 6,
        f"Declarant name: {certificate.part_a_declarant_name}\n\n"
        f"Device particulars:\n{certificate.part_a_device_particulars}\n\n"
        f"Lawful control declaration:\n{certificate.part_a_lawful_control_statement}",
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "PART B - Technical Expert Verification", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        0, 6,
        f"Technical expert: {certificate.part_b_expert_name}\n\n"
        f"Hash algorithm: {certificate.part_b_hash_algorithm}\n"
        f"Hash value (digital fingerprint):\n{certificate.part_b_hash_value}\n\n"
        f"Statement of proper operation and data integrity:\n"
        f"{certificate.part_b_proper_operation_statement}",
    )
    pdf.ln(6)

    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        0, 5,
        "This certificate was drafted by the FEMAS Legal Compliance Agent from verified "
        "cryptographic evidence and requires human approval by an authorized nodal officer "
        "before it is treated as final for court submission.",
    )

    output_path = output_dir / f"bsa_certificate_{certificate.id}.pdf"
    pdf.output(str(output_path))
    return str(output_path)
