from typing import List, Any

class TaskQueue:
    """FIFO task queue."""

    def __init__(self):
        self._items: List[Any] = []

    def enqueue(self, task: Any) -> None:
        """Add task to the back of the queue."""
        self._items.append(task)

    def dequeue(self) -> Any:
        """Remove and return the front task. Raises IndexError if empty."""
        if not self._items:
            raise IndexError("Queue is empty")
        return self._items.pop(0)

    def size(self) -> int:
        """Return number of tasks in queue."""
        return len(self._items)
