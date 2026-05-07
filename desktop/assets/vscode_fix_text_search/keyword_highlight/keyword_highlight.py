from typing import List

def find_lines_with_keyword(text: str, keyword: str, case_sensitive: bool = True) -> List[str]:
    """Return lines in text that contain keyword. Lines are split by newline."""
    lines = text.splitlines()
    if not case_sensitive:
        keyword = keyword.lower()
    result = []
    for line in lines:
        check = line if case_sensitive else line.lower()
        if keyword in check:
            result.append(line)
    return result

def count_occurrences(text: str, keyword: str) -> int:
    """Count how many times keyword appears in text."""
    if not keyword:
        return 0
    return text.count(keyword)
