from distcluster.steps.sasa import extract_sasa_lines


def test_extract_sasa_lines_keeps_only_get_sasa_relative_rows():
    stdout = """
PyMOL>load model.pdb
 /target//A/MET`1      96% |========= |
random text
/target//A/GLY`2      42% |====      |
PyMOL>quit
"""
    lines = extract_sasa_lines(stdout)
    assert lines == [
        "/target//A/MET`1      96% |========= |",
        "/target//A/GLY`2      42% |====      |",
    ]
