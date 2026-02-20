"""Smoke test: hit health and chat endpoints to verify the API is up."""

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

    if not ok:
        sys.exit(1)
    print("Smoke test passed.")


if __name__ == "__main__":
    main()
