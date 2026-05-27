from distcluster.steps.com import guess_element


def test_guess_element_prefers_explicit_element():
    assert guess_element("C1", "Se") == "SE"


def test_guess_element_falls_back_to_name_prefixes():
    assert guess_element("SE1", None) == "SE"
    assert guess_element("CL", None) == "CL"
    assert guess_element("CA", None) == "C"
