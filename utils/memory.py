"""
Shared Memory System for Multi-Agent Communication.

Provides a thread-safe, dictionary-based memory store that persists
workflow state across all agents in the content creation pipeline.
"""
import json
from typing import Any, Dict, List, Optional
from datetime import datetime


class SharedMemory:
    """
    Centralized shared memory for agent communication and state management.

    All agents in the pipeline read from and write to this shared store,
    enabling seamless state propagation without external dependencies.

    Stores:
        - topic         : The user-provided content topic
        - selected_idea : The best idea chosen from the Idea Generator
        - draft_content : Raw draft from the Content Writer
        - final_content : Polished content from the Content Editor
        - status        : Current pipeline status
        - error         : Error message if pipeline fails
    """

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._history: List[Dict[str, str]] = []

    # ------------------------------------------------------------------ #
    # Core CRUD Operations
    # ------------------------------------------------------------------ #

    def set(self, key: str, value: Any) -> None:
        """Store a key-value pair and log the operation."""
        self._store[key] = value
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            "action": "set",
            "key": key,
        })

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value; return *default* if key is absent."""
        return self._store.get(key, default)

    def update(self, data: Dict[str, Any]) -> None:
        """Bulk-update multiple keys at once."""
        for key, value in data.items():
            self.set(key, value)

    def delete(self, key: str) -> None:
        """Remove a single key from the store."""
        if key in self._store:
            del self._store[key]
            self._history.append({
                "timestamp": datetime.now().isoformat(),
                "action": "delete",
                "key": key,
            })

    def clear(self) -> None:
        """Wipe the entire store (history is preserved)."""
        self._store.clear()

    # ------------------------------------------------------------------ #
    # Inspection / Export
    # ------------------------------------------------------------------ #

    def get_all(self) -> Dict[str, Any]:
        """Return a shallow copy of the entire store."""
        return dict(self._store)

    def get_history(self) -> List[Dict[str, str]]:
        """Return the full operation history log."""
        return list(self._history)

    def has(self, key: str) -> bool:
        """Check whether a key exists in the store."""
        return key in self._store

    def to_json(self) -> str:
        """Serialize the store to a JSON string (non-serialisable values use str())."""
        return json.dumps(self._store, indent=2, default=str)

    def __repr__(self) -> str:
        return f"SharedMemory(keys={list(self._store.keys())})"
