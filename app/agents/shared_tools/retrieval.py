"""Retrieval helpers for agents (e.g. keyword search over text). Stub for Phase 1."""


def search_lines(text: str, lines: list[str], case_sensitive: bool = False) -> list[str]:
    """
    Return lines that contain the given text. Used by agents for simple in-memory search.
    """
    if not text or not lines:
        return []
    needle = text if case_sensitive else text.lower()
    return [
        line
        for line in lines
        if (needle in line) or (not case_sensitive and needle in line.lower())
    ]
