"""Formatting helpers for agent responses."""


def format_bullet_list(items: list[str], bullet: str = "-") -> str:
    """Format a list of strings as bullet points. Used by agents for consistent list output."""
    return "\n".join(f"{bullet} {item}" for item in items) if items else ""
