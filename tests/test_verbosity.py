"""Il contatore di cognitive verbosity deve consumare le keyword composte
prima delle semplici: LEFT JOIN = 1 operatore, non 2."""
from verbosity import cognitive_verbosity, loc


def test_compound_keyword_counted_once(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text("SELECT a FROM t LEFT JOIN u ON t.id = u.id\n", encoding="utf-8")
    # SELECT + FROM + LEFT JOIN = 3 (non 4: JOIN non deve rimatchare)
    assert cognitive_verbosity(f, "sql") == 3


def test_group_by_and_order_by_are_single_operators(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text("SELECT a FROM t GROUP BY a ORDER BY a\n", encoding="utf-8")
    assert cognitive_verbosity(f, "sql") == 4  # SELECT, FROM, GROUP BY, ORDER BY


def test_comments_and_blank_lines_excluded_from_loc(tmp_path):
    f = tmp_path / "q.cypher"
    f.write_text("// commento\n\nMATCH (n) RETURN n\n", encoding="utf-8")
    assert loc(f) == 1
    assert cognitive_verbosity(f, "cypher") == 2  # MATCH, RETURN


def test_sql_and_cypher_logical_operators_counted(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text("SELECT a FROM t WHERE x = 1 AND y = 2 OR NOT z\n", encoding="utf-8")
    # SELECT, FROM, WHERE, AND, OR, NOT
    assert cognitive_verbosity(f, "sql") == 6
