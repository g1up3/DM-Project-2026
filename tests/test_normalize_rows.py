"""normalize_rows e' il cuore della verifica di equivalenza Postgres/Neo4j:
se normalizza male, il benchmark confronta risultati non confrontabili."""
from datetime import date, datetime
from decimal import Decimal

from run_benchmark import normalize_rows


def test_decimal_and_float_collapse_to_same_tuple():
    pg_rows = [("Messi", Decimal("42.12345"))]
    neo_rows = [("Messi", 42.123449999)]
    assert normalize_rows(pg_rows) == normalize_rows(neo_rows)


def test_dates_normalized_to_iso_prefix():
    pg_rows = [(date(2015, 8, 29),)]
    neo_rows = [(datetime(2015, 8, 29, 0, 0),)]
    assert normalize_rows(pg_rows) == normalize_rows(neo_rows)


def test_order_is_irrelevant_but_content_is_not():
    a = [("x", 1), ("y", 2)]
    b = [("y", 2), ("x", 1)]
    c = [("y", 2), ("x", 99)]
    assert normalize_rows(a) == normalize_rows(b)
    assert normalize_rows(a) != normalize_rows(c)


def test_none_preserved():
    assert normalize_rows([(None, 1)]) == {(None, 1): 1}


def test_multiset_distinguishes_duplicate_rows():
    # due omonimi con lo stesso punteggio: stesso set, multiset diverso
    one = [("Mario Rossi", 8)]
    two = [("Mario Rossi", 8), ("Mario Rossi", 8)]
    assert set(normalize_rows(one)) == set(normalize_rows(two))
    assert normalize_rows(one) != normalize_rows(two)
