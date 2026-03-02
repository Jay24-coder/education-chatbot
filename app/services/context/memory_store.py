"""In-memory implementation of ContextStore."""

from typing import Any

from app.services.context.store import ContextStore


def _default_perf_metrics() -> dict[str, Any]:
    return {"quizzes": [], "concept_tests": [], "programming_tests": [], "last_activity": None}


def _default_perf_summary() -> dict[str, Any]:
    return {
        "avg_score": 0.0,
        "weak_topics": [],
        "strong_topics": [],
        "alert_flag": False,
    }


class MemoryStore:
    """Minimal in-memory ContextStore for session and conversation state."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._history: dict[str, list[dict[str, Any]]] = {}
        self._perf_metrics: dict[str, dict[str, Any]] = {}
        self._perf_summary: dict[str, dict[str, Any]] = {}

    def get(self, session_id: str, key: str | None = None) -> dict[str, Any]:
        session = self._sessions.get(session_id, {})
        if key is None:
            return dict(session)
        return {key: session[key]} if key in session else {}

    def set(self, session_id: str, key: str, value: Any) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = {}
        self._sessions[session_id][key] = value

    def set_many(self, session_id: str, data: dict[str, Any]) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = {}
        self._sessions[session_id].update(data)

    def append_message(self, session_id: str, user_id: str, role: str, content: str) -> None:
        if session_id not in self._history:
            self._history[session_id] = []
        self._history[session_id].append({"role": role, "content": content})

    def get_history(self, session_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        history = self._history.get(session_id, [])
        if limit is not None:
            history = history[-limit:]
        return list(history)

    def delete(self, session_id: str, key: str | None = None) -> None:
        if key is None:
            self._sessions.pop(session_id, None)
            self._history.pop(session_id, None)
        elif session_id in self._sessions:
            self._sessions[session_id].pop(key, None)

    # --- Performance / assessment metrics (Phase 2) ---

    def append_assessment_result(self, user_id: str, result: dict[str, Any]) -> None:
        if user_id not in self._perf_metrics:
            self._perf_metrics[user_id] = _default_perf_metrics()
        metrics = self._perf_metrics[user_id]
        result_type = (result.get("type") or "").lower()
        if result_type == "quiz":
            metrics["quizzes"].append(result)
        elif result_type == "concept_test":
            metrics["concept_tests"].append(result)
        elif result_type == "programming_test":
            metrics["programming_tests"].append(result)
        metrics["last_activity"] = result.get("timestamp")

    def get_performance_summary(self, user_id: str) -> dict[str, Any]:
        if user_id not in self._perf_summary:
            return _default_perf_summary()
        return dict(self._perf_summary[user_id])

    def update_summary(self, user_id: str) -> None:
        metrics = self._perf_metrics.get(user_id, _default_perf_metrics())
        all_results = (
            list(metrics["quizzes"])
            + list(metrics["concept_tests"])
            + list(metrics.get("programming_tests", []))
        )
        recent = all_results[-5:] if len(all_results) >= 5 else all_results
        scores = [r.get("score") for r in recent if isinstance(r.get("score"), (int, float))]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        by_topic: dict[str, list[float]] = {}
        for r in all_results:
            t = r.get("topic") or "unknown"
            if t not in by_topic:
                by_topic[t] = []
            s = r.get("score")
            if isinstance(s, (int, float)):
                by_topic[t].append(float(s))
        weak_topics = [
            t for t, s in by_topic.items()
            if s and sum(s) / len(s) < 0.5
        ]
        strong_topics = [
            t for t, s in by_topic.items()
            if s and sum(s) / len(s) >= 0.7
        ]
        alert_flag = avg_score < 0.5 and len(recent) >= 5
        if user_id not in self._perf_summary:
            self._perf_summary[user_id] = _default_perf_summary()
        self._perf_summary[user_id].update({
            "avg_score": round(avg_score, 4),
            "weak_topics": weak_topics,
            "strong_topics": strong_topics,
            "alert_flag": alert_flag,
        })
