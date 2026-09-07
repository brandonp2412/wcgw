"""
Tests specifically for complex bash parsing scenarios.
"""

from wcgw.client.bash_state.parser.bash_statement_parser import BashStatementParser


def test_semicolon_lists():
    """Test parsing of semicolon-separated commands."""
    parser = BashStatementParser()

    statements = parser.parse_string("echo a; echo b")
    assert len(statements) == 2
    assert statements[0].text.strip() == "echo a"
    assert statements[1].text.strip() == "echo b"

    statements = parser.parse_string("echo a; echo b; echo c")
    assert len(statements) == 3
    assert statements[0].text.strip() == "echo a"
    assert statements[1].text.strip() == "echo b"
    assert statements[2].text.strip() == "echo c"

    statements = parser.parse_string("echo a  ;  echo b")
    assert len(statements) == 2
    assert statements[0].text.strip() == "echo a"
    assert statements[1].text.strip() == "echo b"


def test_bash_command_with_semicolons_in_quotes():
    """Test that semicolons inside quotes don't split statements."""
    parser = BashStatementParser()

    statements = parser.parse_string("echo 'a;b'")
    assert len(statements) == 1

    statements = parser.parse_string('echo "a;b"')
    assert len(statements) == 1

    statements = parser.parse_string("echo \"a;b\" ; echo 'c;d'")
    assert len(statements) == 2


def test_complex_commands():
    """Test complex command scenarios."""
    parser = BashStatementParser()

    statements = parser.parse_string("cat > file.txt << EOF\ntest\nEOF\n; echo done")
    assert len(statements) == 2

    statements = parser.parse_string("(cd /tmp && echo 'in tmp'); echo 'outside'")
    assert len(statements) == 2

    statements = parser.parse_string("{ echo a; echo b; }; echo c")
    assert len(statements) == 2


def test_command_chaining():
    """Test command chains are treated as a single statement."""
    parser = BashStatementParser()

    statements = parser.parse_string("echo a && echo b")
    assert len(statements) == 1

    statements = parser.parse_string("echo a || echo b")
    assert len(statements) == 1

    statements = parser.parse_string("echo a | grep a")
    assert len(statements) == 1

    statements = parser.parse_string("echo a && echo b || echo c")
    assert len(statements) == 1
