from ai_income_snapshot.intel.contact_finder import (
    extract_emails_from_text,
    infer_domain_email,
    sanitize_email,
    score_email_candidate,
)


def test_extract_emails_from_text_deduplicates_and_sanitizes():
    html = """
    <p>Escribe a INFO@empresa-demo.com.</p>
    <p>También a comercial@empresa-demo.com, gracias.</p>
    <p>También a info@empresa-demo.com</p>
    """
    emails = extract_emails_from_text(html)
    assert "info@empresa-demo.com" in emails
    assert "comercial@empresa-demo.com" in emails
    assert len(emails) == 2


def test_sanitize_email_filters_invalid_domains():
    assert sanitize_email("test@example.com") == ""
    assert sanitize_email("ventas@empresa.com") == "ventas@empresa.com"


def test_score_email_candidate_prefers_generic_local_and_matching_domain():
    score = score_email_candidate("contacto@empresa.com", "empresa.com")
    assert score >= 0.8


def test_infer_domain_email_uses_default_contact():
    email = infer_domain_email("empresa.com", "Empresa Legal")
    assert email == "subvenciones@empresa.com"
