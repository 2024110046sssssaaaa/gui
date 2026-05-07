from typing import List

class Checklist:
    """Simple checklist: add item, check off, list unchecked."""

    def __init__(self):
        self._items: List[dict] = []  # [{"label": str, "done": bool}, ...]

    def add(self, label: str) -> None:
        """Add an unchecked item."""
        self._items.append({"label": label, "done": False})

    def check(self, label: str) -> bool:
        """Mark item as done by label. Return True if found."""
        for item in self._items:
            if item["label"] == label:
                item["done"] = True
                return True
        return False

    def unchecked(self) -> List[str]:
        """Return list of labels that are not done."""
        return [item["label"] for item in self._items if not item["done"]]
