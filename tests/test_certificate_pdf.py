from app.models.certificate import BSACertificate, CertificateStatus
from app.models.evidence import Evidence, EvidenceType
from app.services.certificate_pdf import render_bsa_certificate_pdf


def test_render_bsa_certificate_pdf_creates_valid_pdf(tmp_path):
    evidence = Evidence(
        id="ev-1",
        case_id="case-1",
        evidence_type=EvidenceType.CHAT_EXPORT,
        original_filename="chat.txt",
        storage_path=str(tmp_path / "chat.txt"),
        device_model="Pixel 8",
        device_imei="123456789012345",
        device_os="Android 14",
        sha256_hash="a" * 64,
        md5_hash="b" * 32,
        uploaded_by_id="user-1",
    )
    certificate = BSACertificate(
        id="cert-1",
        evidence_id="ev-1",
        case_id="case-1",
        part_a_declarant_name="Investigating Officer",
        part_a_device_particulars="Model: Pixel 8",
        part_a_lawful_control_statement="Seized under panchnama.",
        part_b_expert_name="FEMAS Examiner",
        part_b_hash_algorithm="SHA-256",
        part_b_hash_value="a" * 64,
        part_b_proper_operation_statement="Device operated normally.",
        status=CertificateStatus.PENDING_APPROVAL,
        generated_by_id="user-1",
    )

    output_path = render_bsa_certificate_pdf(certificate, evidence, tmp_path / "certs")

    pdf_bytes = open(output_path, "rb").read()
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 500
