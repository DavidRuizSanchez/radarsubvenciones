from ai_income_snapshot.intel.website_signals import (
    WebsiteSignalAnalyzer,
    extract_company_summary,
    extract_visible_text,
)


def test_extract_company_summary_prefers_meta_description():
    html = """
    <html><head>
      <meta name="description" content="Somos una consultora tecnológica que ayuda a pymes a digitalizarse." />
      <title>Acme · Consultoría digital</title>
    </head><body><p>Otro texto</p></body></html>
    """
    summary = extract_company_summary(html, extract_visible_text(html))
    assert summary.startswith("Somos una consultora")


def test_extract_company_summary_falls_back_to_title():
    html = """
    <html><head><title>Industrias MALPE · Fabricación de reprografía</title></head>
    <body>texto del cuerpo</body></html>
    """
    summary = extract_company_summary(html, extract_visible_text(html))
    assert "MALPE" in summary


def test_extract_company_summary_falls_back_to_visible_text_for_short_titles():
    # Título vacío y sin meta: usa el body.
    html = "<html><head><title></title></head><body><p>Fabricamos piezas de precisión para automoción desde 1975 en Zaragoza.</p></body></html>"
    summary = extract_company_summary(html, extract_visible_text(html))
    assert "precisión" in summary or "precision" in summary


def test_extract_company_summary_empty_when_no_content():
    assert extract_company_summary("", "") == ""


def test_analyze_missing_website_returns_empty_summary():
    analyzer = WebsiteSignalAnalyzer()
    signal = analyzer.analyze(None)
    assert signal.company_summary == ""
    assert signal.sample_excerpt == ""
