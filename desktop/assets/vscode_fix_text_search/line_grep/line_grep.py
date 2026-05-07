from typing import List, Tuple

def grep_lines(content: str, pattern: str) -> List[Tuple[int, str]]:
    """Return (line_number, line_content) for each line containing pattern. Line numbers 1-based."""
    lines = content.splitlines()
    return [(i + 1, line) for i, line in enumerate(lines) if pattern in line]

def grep_count(content: str, pattern: str) -> int:
    """Count lines that contain pattern."""
    return len(grep_lines(content, pattern))
