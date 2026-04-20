from ai_income_snapshot.intel.website_guesser import (
    candidate_urls,
    slugify_company_name,
)


def test_slugify_strips_societary_suffixes():
    assert slugify_company_name("RM CONSULTORIA DE EMPRESAS SOCIEDAD LIM") == "rmconsultoriadeempresas"
    assert slugify_company_name("Talleres del Norte S.L.") == "talleresdelnorte"
    assert slugify_company_name("Grupo Atisa, S.A.") == "grupoatisa"


def test_slugify_handles_accents_and_punctuation():
    assert slugify_company_name("Gestión & Innovación, S.L.") == "gestioninnovacion"


def test_candidate_urls_are_generated_in_order():
    urls = candidate_urls("Grupo Atisa SA")
    assert urls == ["https://www.grupoatisa.es", "https://www.grupoatisa.com"]


def test_candidate_urls_empty_for_too_short_slug():
    # Nombres como "SL" o solo sufijos societarios deberían descartarse.
    assert candidate_urls("SL") == []
    assert candidate_urls("S.A.") == []
