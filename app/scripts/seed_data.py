"""Optional seed script for Phase 1. In-memory context and stubbed agents need no DB seed."""

def main() -> None:
    print("Phase 1: no seed data required (in-memory context, stubbed syllabus/admin/topic data).")
    print("Run with: uv run python -m app.scripts.seed_data")


if __name__ == "__main__":
    main()
