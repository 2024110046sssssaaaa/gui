def reverse_string(s: str) -> str:
    """Return the reversed string."""
    return s[::-1]

def is_palindrome(s: str) -> bool:
    """Check if string is palindrome (ignore case, strip spaces)."""
    t = "".join(c.lower() for c in s if c.isalnum())
    return t == t[::-1]
