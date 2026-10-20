from tranquera.textutil import contains_phrase, fold, squash, stem, tokens


def test_fold_removes_accents_and_case():
    assert fold("Contraseña ÚNICA") == "contrasena unica"


def test_stem_matches_plurals():
    assert stem("respaldos") == stem("respaldo")
    assert stem("revisiones") == stem("revision")


def test_phrase_matching_is_order_sensitive():
    hay = tokens("Se realiza la revisión de accesos cada trimestre")
    assert contains_phrase(hay, tokens("revision de accesos"))
    assert not contains_phrase(hay, tokens("accesos revision"))


def test_squash_normalizes_quotes():
    assert squash('  "Cada   trimestre."  ') == "cada trimestre"
