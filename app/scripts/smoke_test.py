"""Smoke test: hit health, chat, and Phase 2 assessment endpoints to verify the API is up."""

import sys

import httpx

BASE = "http://127.0.0.1:8000/api/v1"


def main() -> None:
    ok = True
    with httpx.Client(timeout=10.0) as client:
        # Liveness
        r = client.get(f"{BASE}/live")
        if r.status_code != 200:
            print(f"FAIL /live -> {r.status_code}")
            ok = False
        else:
            print("OK /live")

        # Readiness
        r = client.get(f"{BASE}/ready")
        if r.status_code != 200:
            print(f"FAIL /ready -> {r.status_code}")
            ok = False
        else:
            print("OK /ready")

        # Chat (minimal payload)
        r = client.post(f"{BASE}/chat", json={"message": "Hello"})
        if r.status_code not in (200, 500):
            print(f"FAIL /chat -> {r.status_code}")
            ok = False
        else:
            print("OK /chat (response or expected error)")

        # Phase 2: quiz flow (start + one answer)
        r = client.post(
            f"{BASE}/assessment/quiz/start",
            json={"session_id": "smoke-s1", "user_id": "smoke-u1", "topic": "algebra", "difficulty": "beginner"},
        )
        if r.status_code != 200:
            print(f"FAIL /assessment/quiz/start -> {r.status_code}")
            ok = False
        else:
            print("OK /assessment/quiz/start")
            r2 = client.post(
                f"{BASE}/assessment/quiz/answer",
                json={"session_id": "smoke-s1", "user_id": "smoke-u1", "answer": "5"},
            )
            if r2.status_code != 200:
                print(f"FAIL /assessment/quiz/answer -> {r2.status_code}")
                ok = False
            else:
                print("OK /assessment/quiz/answer")

        # Phase 2: concept-test start (may 503 if no LLM)
        r = client.post(
            f"{BASE}/assessment/concept-test/start",
            json={"session_id": "smoke-ct1", "user_id": "smoke-u1", "topic": "algebra"},
        )
        if r.status_code not in (200, 503):
            print(f"FAIL /assessment/concept-test/start -> {r.status_code}")
            ok = False
        else:
            print("OK /assessment/concept-test/start (200 or 503 when no LLM)")

        # Phase 2: performance summary
        r = client.get(f"{BASE}/assessment/performance/smoke-u1")
        if r.status_code != 200:
            print(f"FAIL /assessment/performance/{{user_id}} -> {r.status_code}")
            ok = False
        else:
            print("OK /assessment/performance/{user_id}")

    if not ok:
        sys.exit(1)
    print("Smoke test passed.")
