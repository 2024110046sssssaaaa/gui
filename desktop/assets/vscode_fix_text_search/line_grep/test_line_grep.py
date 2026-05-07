import unittest
from line_grep import grep_lines, grep_count

class TestLineGrep(unittest.TestCase):
    def test_grep_lines(self):
        content = "first\nsecond line\nthird\nsecond again"
        self.assertEqual(grep_lines(content, "second"), [(2, "second line"), (4, "second again")])
        self.assertEqual(grep_lines(content, "missing"), [])

    def test_grep_count(self):
        content = "a\nb\na\nc"
        self.assertEqual(grep_count(content, "a"), 2)
