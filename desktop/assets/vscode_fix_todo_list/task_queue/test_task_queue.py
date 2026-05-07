import unittest
from task_queue import TaskQueue

class TestTaskQueue(unittest.TestCase):
    def test_enqueue_dequeue(self):
        q = TaskQueue()
        q.enqueue("a")
        q.enqueue("b")
        self.assertEqual(q.dequeue(), "a")
        self.assertEqual(q.dequeue(), "b")
        with self.assertRaises(IndexError):
            q.dequeue()

    def test_size(self):
        q = TaskQueue()
        self.assertEqual(q.size(), 0)
        q.enqueue(1)
        q.enqueue(2)
        self.assertEqual(q.size(), 2)
        q.dequeue()
        self.assertEqual(q.size(), 1)
