"""
File with definitions of known source code file extensions.
Used to determine the appropriate context length for files.
Supports selecting between coding_max_tokens and noncoding_max_tokens
based on file extensions.
"""
from typing import Dict, Optional, Set

SOURCE_CODE_EXTENSIONS: Set[str] = {
    'py', 'pyx', 'pyi', 'pyw',
    'js', 'jsx', 'ts', 'tsx', 'mjs', 'cjs',
    'html', 'htm', 'xhtml', 'css', 'scss', 'sass', 'less',
    'c', 'h', 'cpp', 'cxx', 'cc', 'hpp', 'hxx', 'hh', 'inl',
    'cs', 'csx',
    'java', 'scala', 'kt', 'kts', 'groovy',
    'go', 'mod',
    'rs', 'rlib',
    'swift',
    'rb', 'rake', 'gemspec',
    'php', 'phtml', 'phar', 'phps',
    'sh', 'bash', 'zsh', 'fish',
    'ps1', 'psm1', 'psd1',
    'sql', 'ddl', 'dml',
    'xml', 'json', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'conf',
    'md', 'markdown', 'rst', 'adoc', 'tex',
    'Makefile', 'Dockerfile', 'Jenkinsfile',
    'hs', 'lhs',
    'lisp', 'cl', 'el', 'clj', 'cljs', 'edn', 'scm',
    'erl', 'hrl', 'ex', 'exs',
    'dart',
    'm', 'mm',
}

CONTEXT_LENGTH_LIMITS: Dict[str, int] = {
    'source_code': 24000,
    'default': 8000,
}

def is_source_code_file(filename: str) -> bool:
    """
    Determine if a file is a source code file based on its extension.
    
    Args:
        filename: The name of the file to check
        
    Returns:
        True if the file has a recognized source code extension, False otherwise
    """
    parts = filename.split('.')
    if len(parts) > 1:
        ext = parts[-1].lower()
        return ext in SOURCE_CODE_EXTENSIONS
    
    return filename.lower() in {ext.lower() for ext in SOURCE_CODE_EXTENSIONS}

def get_context_length_for_file(filename: str) -> int:
    """
    Get the appropriate context length limit for a file based on its extension.
    
    Args:
        filename: The name of the file to check
        
    Returns:
        The context length limit in tokens
    """
    if is_source_code_file(filename):
        return CONTEXT_LENGTH_LIMITS['source_code']
    return CONTEXT_LENGTH_LIMITS['default']


def select_max_tokens(filename: str, coding_max_tokens: Optional[int], noncoding_max_tokens: Optional[int]) -> Optional[int]:
    """
    Select the appropriate max_tokens limit based on file type.
    
    Args:
        filename: The name of the file to check
        coding_max_tokens: Maximum tokens for source code files
        noncoding_max_tokens: Maximum tokens for non-source code files
        
    Returns:
        The appropriate max_tokens limit for the file
    """
    if coding_max_tokens is None and noncoding_max_tokens is None:
        return None
        
    if is_source_code_file(filename):
        return coding_max_tokens
    return noncoding_max_tokens
