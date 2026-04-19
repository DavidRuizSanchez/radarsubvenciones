from ai_income_snapshot.clients.bdns_client import split_beneficiary


def test_split_beneficiary_with_visible_cif():
    cif, name = split_beneficiary("B12345678 EMPRESA DEMO SL")
    assert cif == "B12345678"
    assert name == "EMPRESA DEMO SL"


def test_split_beneficiary_with_masked_cif():
    cif, name = split_beneficiary("***7257** AHINITZ GERRIKAGOITIA SAGARNA")
    assert cif is None
    assert name == "AHINITZ GERRIKAGOITIA SAGARNA"


def test_split_beneficiary_without_cif_prefix():
    cif, name = split_beneficiary("FUNDACION CULTURAL METROPOLITANA")
    assert cif is None
    assert name == "FUNDACION CULTURAL METROPOLITANA"
