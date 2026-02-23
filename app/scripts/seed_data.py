"""Optional seed script. Phase 1: in-memory context, no DB seed. Phase 2: question bank is in-code."""

from app.agents.shared_tools.question_bank import DifficultyLevel, QuestionBank, TopicArea


def main() -> None:
    print("Phase 1: no DB seed required (in-memory context, stubbed syllabus/admin/topic data).")
    # Phase 2: question bank seeding is in-code; report availability per topic/difficulty
    qb = QuestionBank()
    print("Phase 2: question bank (in-code seed data) loaded.")
    for topic in TopicArea:
        for diff in DifficultyLevel:
            count = len(qb.get_questions(topic, diff, 999))
            if count:
                print(f"  - {topic.value} / {diff.value}: {count} questions")
    print("Run with: uv run python -m app.scripts.seed_data")


if __name__ == "__main__":
    main()
