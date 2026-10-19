from novapanel import i18n


def test_tables_have_same_keys():
    en, fr = i18n.STRINGS["en"], i18n.STRINGS["fr"]
    assert en.keys() == fr.keys()
    for k, v in en.items():
        assert type(v) is type(fr[k]) and (not isinstance(v, list) or len(v) == len(fr[k])), k


def test_resolve_language():
    assert i18n.resolve("en", "fr_FR") == "en"
    assert i18n.resolve("fr", "en-US") == "fr"
    assert i18n.resolve("auto", "fr-CA") == "fr"
    assert i18n.resolve("auto", "de_DE") == "en"
    assert i18n.resolve("auto", "") == "en"
    assert i18n.resolve("bogus", "C") == "en"
