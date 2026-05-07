import unittest
from keyword_highlight import find_lines_with_keyword, count_occurrences

class TestKeywordHighlight(unittest.TestCase):
    def test_find_lines_with_keyword(self):
        text = "Hello World\nThis is a test\nHello again\nno match"
        self.assertEqual(find_lines_with_keyword(text, "Hello"), ["Hello World", "Hello again"])
        self.assertEqual(find_lines_with_keyword(text, "hello", case_sensitive=False), ["Hello World", "Hello again"])
        self.assertEqual(find_lines_with_keyword(text, "xyz"), [])

    def test_count_occurrences(self):
        self.assertEqual(count_occurrences("aaa bbb aaa", "aaa"), 2)
        self.assertEqual(count_occurrences("", "a"), 0)
