from collections import Counter

from tranquera.catalog import iso_controls, nist_catalog


def test_annex_a_has_93_controls_in_four_themes():
    controls = iso_controls()
    assert len(controls) == 93
    assert len({c.id for c in controls}) == 93
    assert Counter(c.theme for c in controls) == {"organizational": 37, "people": 8, "physical": 14, "technological": 34}


def test_nist_csf_2_structure():
    nist = nist_catalog()
    assert len(nist.functions) == 6
    assert len(nist.categories) == 22
    assert len(nist.subcategories) == 106
    for sub in nist.subcategories:
        assert nist.category_of(sub) in nist.categories


def test_every_mapping_points_to_a_real_subcategory():
    subs = nist_catalog().subcategories
    for c in iso_controls():
        for ref in c.nist:
            assert ref in subs, f"{c.id} maps to unknown {ref}"


def test_every_control_has_titles_and_keywords():
    for c in iso_controls():
        assert c.title_es and c.title_en and c.keywords
