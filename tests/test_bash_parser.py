"""
Tests for the bash statement parser.
"""

from wcgw.client.bash_state.parser.bash_statement_parser import BashStatementParser


def test_bash_statement_parser_basic() -> None:
    """Test basic statement parsing."""
    parser = BashStatementParser()
    
    statements = parser.parse_string("echo hello")
    assert len(statements) == 1
    assert statements[0].text == "echo hello"
    
    statements = parser.parse_string('echo "hello\nworld"')
    assert len(statements) == 1
    
    statements = parser.parse_string("echo hello && echo world")
    assert len(statements) == 1
    
    statements = parser.parse_string("echo hello || echo world")
    assert len(statements) == 1
    
    statements = parser.parse_string("echo hello | grep hello")
    assert len(statements) == 1


def test_bash_statement_parser_multiple() -> None:
    """Test multiple statement detection."""
    parser = BashStatementParser()
    
    statements = parser.parse_string("echo hello\necho world")
    assert len(statements) == 2
    
    statements = parser.parse_string("echo hello; echo world")
    assert len(statements) == 2
    
    statements = parser.parse_string("echo hello; echo world && echo again")
    assert len(statements) == 2
    
    statements = parser.parse_string("echo a; echo b\necho c")
    assert len(statements) == 3


def test_bash_statement_parser_complex() -> None:
    """Test complex statement handling."""
    parser = BashStatementParser()
    
    statements = parser.parse_string("(echo hello; echo world)")
    assert len(statements) == 1
    
    statements = parser.parse_string("{ echo hello; echo world; }")
    assert len(statements) == 1
    
    statements = parser.parse_string('echo "hello;world"')
    assert len(statements) == 1
    
    statements = parser.parse_string('echo hello\\; echo world')
    assert len(statements) == 1
    
    statements = parser.parse_string("echo 'hello;world'")
    assert len(statements) == 1


def test_comments() -> None:
    """Test comment handling."""
    parser = BashStatementParser()

    statements = parser.parse_string("# Test\nls")
    assert len(statements) == 2
    assert statements[0].text == "# Test"
    assert statements[0].node_type == "comment"
    assert statements[1].text == "ls"

    statements = parser.parse_string("# Comment 1\n# Comment 2\necho hello")
    assert len(statements) == 3
    assert statements[0].node_type == "comment"
    assert statements[1].node_type == "comment"
    assert statements[2].node_type == "command"

    statements = parser.parse_string("echo hello # inline comment")
    assert len(statements) == 2
    assert statements[0].text == "echo hello"
    assert statements[0].node_type == "command"
    assert statements[1].text == "# inline comment"
    assert statements[1].node_type == "comment"

    statements = parser.parse_string("# Comment\necho a; echo b")
    assert len(statements) == 3
    assert statements[0].node_type == "comment"

    statements = parser.parse_string("# Just a comment")
    assert len(statements) == 1
    assert statements[0].node_type == "comment"

    statements = parser.parse_string("# Comment 1\n\n# Comment 2\n\nls")
    assert len(statements) == 3
    assert statements[0].node_type == "comment"
    assert statements[1].node_type == "comment"
    assert statements[2].node_type == "command"


def test_complete_control_structures() -> None:
    """Test that complete control structures are treated as single statements."""
    parser = BashStatementParser()

    statements = parser.parse_string("if [ -f file ]; then\n  echo found\nfi")
    assert len(statements) == 1
    assert statements[0].node_type == "if_statement"

    statements = parser.parse_string("for i in 1 2 3; do\n  echo $i\ndone")
    assert len(statements) == 1
    assert statements[0].node_type == "for_statement"

    statements = parser.parse_string("while true; do\n  echo loop\n  break\ndone")
    assert len(statements) == 1
    assert statements[0].node_type == "while_statement"

    statements = parser.parse_string(
        'case $var in\n  a) echo A ;;\n  b) echo B ;;\nesac'
    )
    assert len(statements) == 1
    assert statements[0].node_type == "case_statement"

    statements = parser.parse_string("function myfunc() {\n  echo hello\n}")
    assert len(statements) == 1
    assert statements[0].node_type == "function_definition"


def test_multiline_strings() -> None:
    """Test that multi-line strings in quotes are treated as single statements."""
    parser = BashStatementParser()

    statements = parser.parse_string('echo "line 1\nline 2\nline 3"')
    assert len(statements) == 1
    assert statements[0].node_type == "command"

    statements = parser.parse_string("echo 'line 1\nline 2\nline 3'")
    assert len(statements) == 1
    assert statements[0].node_type == "command"


def test_line_continuation() -> None:
    """Test that line continuations with backslash are treated as single statements."""
    parser = BashStatementParser()

    statements = parser.parse_string("echo hello \\\n  world \\\n  again")
    assert len(statements) == 1
    assert statements[0].node_type == "command"

    statements = parser.parse_string("echo a \\\n  b\necho c")
    assert len(statements) == 2


def test_here_documents() -> None:
    """Test that here documents are treated as single statements."""
    parser = BashStatementParser()

    statements = parser.parse_string("cat <<EOF\nline 1\nline 2\nEOF")
    assert len(statements) == 1
    assert statements[0].node_type == "redirected_statement"

    statements = parser.parse_string("cat <<EOF\ndata\nEOF\necho done")
    assert len(statements) == 2


def test_subshells_and_command_substitution() -> None:
    """Test subshells and command substitution."""
    parser = BashStatementParser()

    statements = parser.parse_string("(cd /tmp && ls)")
    assert len(statements) == 1
    assert statements[0].node_type == "subshell"

    statements = parser.parse_string("result=$(echo hello)")
    assert len(statements) == 1
    assert statements[0].node_type == "variable_assignment"

    statements = parser.parse_string("echo $(echo $(echo nested))")
    assert len(statements) == 1
    assert statements[0].node_type == "command"


def test_compound_statements() -> None:
    """Test compound statements with braces."""
    parser = BashStatementParser()

    statements = parser.parse_string("{ echo a; echo b; }")
    assert len(statements) == 1
    assert statements[0].node_type == "compound_statement"

    statements = parser.parse_string("{\n  echo a\n  echo b\n}")
    assert len(statements) == 1
    assert statements[0].node_type == "compound_statement"


def test_complex_pipelines() -> None:
    """Test complex pipelines and command chains."""
    parser = BashStatementParser()

    statements = parser.parse_string("cat file | \\\n  grep pattern | \\\n  sort")
    assert len(statements) == 1
    assert statements[0].node_type == "pipeline"

    statements = parser.parse_string("cmd1 && \\\n  cmd2 || \\\n  cmd3")
    assert len(statements) == 1
    assert statements[0].node_type == "list"


def test_mixed_complete_statements() -> None:
    """Test mixing different types of complete statements."""
    parser = BashStatementParser()

    statements = parser.parse_string(
        "myfunc() {\n  echo hello\n}\nmyfunc\necho done"
    )
    assert len(statements) == 3
    assert statements[0].node_type == "function_definition"
    assert statements[1].node_type == "command"
    assert statements[2].node_type == "command"

    statements = parser.parse_string("if true; then\n  echo yes\nfi\necho after")
    assert len(statements) == 2
    assert statements[0].node_type == "if_statement"
    assert statements[1].node_type == "command"

    statements = parser.parse_string(
        "# Setup\nexport VAR=value\nfor i in 1 2; do\n  echo $i\ndone"
    )
    assert len(statements) == 3
    assert statements[0].node_type == "comment"
    assert statements[1].node_type == "declaration_command"
    assert statements[2].node_type == "for_statement"
