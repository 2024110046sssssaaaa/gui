import unittest
from checklist import Checklist

class TestChecklist(unittest.TestCase):
    def test_add_and_unchecked(self):
        c = Checklist()
        c.add("buy milk")
        c.add("call mom")
        self.assertEqual(c.unchecked(), ["buy milk", "call mom"])

    def test_check(self):
        c = Checklist()
        c.add("a")
        c.add("b")
        self.assertTrue(c.check("a"))
        self.assertEqual(c.unchecked(), ["b"])
        self.assertFalse(c.check("c"))
