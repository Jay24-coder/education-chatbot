"""In-memory question bank with LLM fallback for Quiz and Concept Test agents (Phase 2)."""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.llm.provider import LLMProvider


class DifficultyLevel(str, Enum):
    """Difficulty level for questions; aligned with syllabus KB."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class TopicArea(str, Enum):
    """Topic areas aligned with syllabus / curriculum (math and physics)."""

    ALGEBRA = "algebra"
    CALCULUS = "calculus"
    KINEMATICS = "kinematics"
    WAVES = "waves"


@dataclass
class Question:
    """Single question: seed or LLM-generated."""

    topic: str
    difficulty: str
    text: str
    correct_answer: str
    options: list[str] = field(default_factory=list)
    source: str = "seed"  # "seed" | "llm"


def _normalize_topic_difficulty(topic: str | TopicArea, difficulty: str | DifficultyLevel) -> tuple[str, str]:
    t = topic.value if isinstance(topic, TopicArea) else (topic or "").strip().lower()
    d = difficulty.value if isinstance(difficulty, DifficultyLevel) else (difficulty or "").strip().lower()
    return t, d


def _seed_questions() -> list[Question]:
    """Seed ~20--30 questions per major topic at three difficulty levels."""
    qs: list[Question] = []
    # Algebra
    for diff, items in [
        ("beginner", [
            ("What is 2 + 3?", "5", ["3", "5", "6", "7"]),
            ("Solve x + 5 = 12 for x.", "7", ["5", "6", "7", "17"]),
            ("What is 3 × 4?", "12", ["7", "12", "14", "16"]),
            ("Simplify: 2x + 3x.", "5x", ["5x", "6x", "5", "6"]),
            ("What is 10 − 4?", "6", ["4", "5", "6", "14"]),
            ("Solve 2x = 10 for x.", "5", ["4", "5", "8", "12"]),
        ]),
        ("intermediate", [
            ("Factor x² − 4.", "(x-2)(x+2)", ["(x-2)(x+2)", "(x-4)(x+1)", "x(x-4)", "cannot factor"]),
            ("Solve x² = 9.", "x = 3 or x = -3", ["3", "-3", "3 or -3", "9"]),
            ("Expand (x+1)(x+2).", "x²+3x+2", ["x²+3x+2", "x²+2x+2", "2x+3", "x²+2"]),
            ("What is the slope of y = 2x + 3?", "2", ["2", "3", "5", "2x"]),
            ("Solve 3x − 7 = 2.", "x = 3", ["3", "2", "5", "9"]),
            ("Simplify (x³)(x²).", "x^5", ["x^5", "x^6", "x", "2x^5"]),
        ]),
        ("advanced", [
            ("Solve the quadratic x² − 5x + 6 = 0.", "x = 2 or x = 3", ["2 and 3", "1 and 6", "-2 and -3", "0"]),
            ("What is log₂(8)?", "3", ["2", "3", "4", "8"]),
            ("Solve |x − 3| = 5.", "x = 8 or x = -2", ["8", "-2", "8 or -2", "2"]),
            ("Sum of roots of x² − 6x + 8 = 0?", "6", ["6", "8", "-6", "2"]),
            ("Simplify √(x²) for x ≥ 0.", "x", ["x", "|x|", "-x", "x²"]),
            ("Solve 2^(x+1) = 16.", "x = 3", ["2", "3", "4", "15"]),
        ]),
    ]:
        for text, correct, opts in items:
            qs.append(Question(topic="algebra", difficulty=diff, text=text, correct_answer=correct, options=opts))
    # Calculus
    for diff, items in [
        ("beginner", [
            ("What is the derivative of a constant?", "0", ["0", "1", "constant", "x"]),
            ("d/dx(x) = ?", "1", ["0", "1", "x", "2x"]),
            ("What is ∫ 1 dx?", "x + C", ["x", "x + C", "1", "C"]),
            ("d/dx(x²) = ?", "2x", ["x", "2x", "x²", "2"]),
            ("What is the derivative of f(x) + g(x)?", "f'(x) + g'(x)", ["f'+g'", "fg", "f+g", "same"]),
            ("∫ 2x dx = ?", "x² + C", ["x²", "x²+C", "2x²", "2"]),
        ]),
        ("intermediate", [
            ("d/dx(sin x) = ?", "cos x", ["cos x", "-cos x", "sin x", "tan x"]),
            ("∫ cos x dx = ?", "sin x + C", ["sin x", "sin x + C", "-sin x", "cos x + C"]),
            ("What is lim_{x→0} sin(x)/x?", "1", ["0", "1", "undefined", "∞"]),
            ("d/dx(e^x) = ?", "e^x", ["e^x", "xe^(x-1)", "0", "ln x"]),
            ("∫ 1/x dx = ?", "ln|x| + C", ["ln x", "ln|x| + C", "1/x²", "x"]),
            ("Product rule: (fg)' = ?", "f'g + fg'", ["f'g'", "f'g + fg'", "fg", "f' + g'"]),
        ]),
        ("advanced", [
            ("∫₀^1 x² dx = ?", "1/3", ["1/2", "1/3", "1", "2/3"]),
            ("d/dx(ln x) = ?", "1/x", ["1/x", "x", "ln x", "e^x"]),
            ("Integration by parts: ∫ u dv = ?", "uv − ∫ v du", ["uv", "uv - ∫v du", "u'v'", "v du"]),
            ("What is ∫ sec² x dx?", "tan x + C", ["tan x", "tan x + C", "sec x", "cot x"]),
            ("lim_{h→0} (f(x+h)−f(x))/h is the definition of ?", "derivative", ["derivative", "integral", "limit", "slope"]),
            ("∫ e^x dx = ?", "e^x + C", ["e^x", "e^x + C", "xe^x", "e^(x+1) + C"]),
        ]),
    ]:
        for text, correct, opts in items:
            qs.append(Question(topic="calculus", difficulty=diff, text=text, correct_answer=correct, options=opts))
    # Kinematics
    for diff, items in [
        ("beginner", [
            ("What is velocity?", "Speed with direction", ["Speed", "Speed with direction", "Distance", "Acceleration"]),
            ("Unit of acceleration?", "m/s²", ["m/s", "m/s²", "s/m", "m"]),
            ("v = u + at is valid when acceleration is ?", "constant", ["zero", "constant", "variable", "negative"]),
            ("Distance = speed × ?", "time", ["time", "velocity", "acceleration", "mass"]),
            ("What is displacement?", "Change in position (vector)", ["Distance", "Change in position", "Speed", "Time"]),
            ("Deceleration means acceleration is ?", "negative", ["zero", "negative", "positive", "constant"]),
        ]),
        ("intermediate", [
            ("Equation of motion: s = ut + (1/2)at² assumes ?", "constant a", ["a=0", "constant a", "u=0", "t=0"]),
            ("In free fall, a = ?", "g (≈9.8 m/s²)", ["0", "g", "2g", "-g only"]),
            ("Area under v-t graph gives ?", "displacement", ["velocity", "displacement", "acceleration", "time"]),
            ("Slope of position-time graph is ?", "velocity", ["distance", "velocity", "acceleration", "speed"]),
            ("v² = u² + 2as relates ?", "v, u, a, s", ["v,u,a,s", "v,u,t,s", "v,a,t", "u,a,t"]),
            ("Average velocity = ?", "total displacement / total time", ["distance/time", "displacement/time", "speed/2", "u+v"]),
        ]),
        ("advanced", [
            ("Projectile: horizontal acceleration = ?", "0", ["0", "g", "-g", "v₀"]),
            ("Range of projectile (same level) is maximum when angle = ?", "45°", ["0°", "45°", "90°", "30°"]),
            ("Centripetal acceleration direction?", "toward center", ["tangent", "toward center", "outward", "constant"]),
            ("Angular velocity ω = ?", "dθ/dt", ["θ/t", "dθ/dt", "v/r", "a/r"]),
            ("For constant angular acceleration, θ = ?", "ω₀t + (1/2)αt²", ["ωt", "ω₀t + ½αt²", "ω/t", "αt"]),
            ("Relative velocity v_A - v_B is velocity of A in frame of ?", "B", ["ground", "B", "A", "center"]),
        ]),
    ]:
        for text, correct, opts in items:
            qs.append(Question(topic="kinematics", difficulty=diff, text=text, correct_answer=correct, options=opts))
    # Waves
    for diff, items in [
        ("beginner", [
            ("What is wavelength λ?", "Distance between two similar points on a wave", ["Time for one cycle", "Distance between peaks", "Height of wave", "Speed"]),
            ("Frequency f = ?", "1 / period", ["1/T", "T", "v/λ", "λ/T"]),
            ("Unit of frequency?", "Hz", ["Hz", "m", "s", "m/s"]),
            ("v = fλ relates ?", "speed, frequency, wavelength", ["v,f,λ", "v,f,T", "a,v,t", "f,T only"]),
            ("Sound is a ? wave.", "longitudinal", ["transverse", "longitudinal", "electromagnetic", "standing"]),
            ("Amplitude is the ? of the wave.", "maximum displacement", ["wavelength", "frequency", "maximum displacement", "speed"]),
        ]),
        ("intermediate", [
            ("Speed of light in vacuum c ≈ ?", "3×10⁸ m/s", ["3×10⁸ m/s", "3×10⁶ m/s", "3×10¹⁰ m/s", "300 m/s"]),
            ("Refraction: n₁ sin θ₁ = ?", "n₂ sin θ₂", ["n₂ sin θ₂", "n₂ cos θ₂", "n₁ sin θ₂", "sin θ₂"]),
            ("Total internal reflection when angle of incidence is ? critical.", "greater than", ["less than", "greater than", "equal to", "none"]),
            ("Doppler: when source approaches, observed frequency ?", "increases", ["increases", "decreases", "same", "zero"]),
            ("Standing wave: nodes are points of ? displacement.", "zero", ["zero", "max", "constant", "variable"]),
            ("Harmonic n has ? nodes (excluding ends).", "n − 1", ["n", "n-1", "n+1", "2n"]),
        ]),
        ("advanced", [
            ("Beat frequency = ?", "|f₁ − f₂|", ["f₁ - f₂", "|f₁ − f₂|", "f₁ + f₂", "average"]),
            ("Phase difference for destructive interference (same freq)?", "π (180°)", ["0", "π", "π/2", "2π"]),
            ("Intensity I ∝ ?", "amplitude²", ["amplitude", "amplitude²", "frequency", "wavelength"]),
            ("Group velocity vs phase velocity: dispersion when ?", "they differ", ["same", "they differ", "v_g=0", "v_p=0"]),
            ("Resonance when driving frequency ? natural frequency.", "equals", ["less than", "equals", "greater than", "twice"]),
            ("Snell's law: n = ?", "c / v", ["c/v", "v/c", "λf", "sin i/sin r"]),
        ]),
    ]:
        for text, correct, opts in items:
            qs.append(Question(topic="waves", difficulty=diff, text=text, correct_answer=correct, options=opts))
    return qs


@dataclass
class QuestionBank:
    """
    In-memory question bank with optional LLM fallback when topic/difficulty has no seed.
    """
    _questions: list[Question] = field(default_factory=_seed_questions)

    def get_questions(
        self,
        topic: str | TopicArea,
        difficulty: str | DifficultyLevel,
        count: int,
    ) -> list[Question]:
        """
        Return up to `count` questions for the given topic and difficulty from the seed bank.
        Uses random sample without replacement. Returns fewer than count if not enough seeds.
        """
        t, d = _normalize_topic_difficulty(topic, difficulty)
        matches = [q for q in self._questions if q.topic == t and q.difficulty == d]
        if not matches:
            return []
        return random.sample(matches, min(count, len(matches)))

    async def get_question(
        self,
        topic: str | TopicArea,
        difficulty: str | DifficultyLevel,
        llm_provider: "LLMProvider | None" = None,
    ) -> Question:
        """
        Return a question for the given topic and difficulty. If none in bank, use LLM
        to generate one (marked source='llm') if llm_provider is provided; otherwise
        return a fallback placeholder question.
        """
        import random
        t, d = _normalize_topic_difficulty(topic, difficulty)
        matches = [q for q in self._questions if q.topic == t and q.difficulty == d]
        if matches:
            return random.choice(matches)
        if llm_provider:
            return await self._generate_via_llm(t, d, llm_provider)
        return Question(
            topic=t,
            difficulty=d,
            text=f"No seed question for {t} / {d}. Configure an LLM for fallback.",
            correct_answer="",
            options=[],
            source="fallback",
        )

    async def _generate_via_llm(self, topic: str, difficulty: str, llm_provider: "LLMProvider") -> Question:
        """Generate one MCQ via LLM; used as fallback."""
        prompt = (
            f"Generate exactly one multiple-choice question for topic '{topic}' at difficulty '{difficulty}'. "
            "Format: first line is the question; next line 'CORRECT: <answer>'; then 'A. option1', 'B. option2', etc. "
            "Use 4 options. Output only the question and options, no extra text."
        )
        try:
            response = await llm_provider.complete(prompt, temperature=0.3)
        except Exception:
            return Question(
                topic=topic,
                difficulty=difficulty,
                text=f"No question available for {topic} / {difficulty}. LLM failed.",
                correct_answer="",
                options=[],
                source="llm",
            )
        text, correct, options = _parse_llm_question(response or "")
        return Question(
            topic=topic,
            difficulty=difficulty,
            text=text or f"Generated question: {topic}, {difficulty}",
            correct_answer=correct or "",
            options=options,
            source="llm",
        )


def _parse_llm_question(response: str) -> tuple[str, str, list[str]]:
    """Parse LLM output into question text, correct answer, and options list."""
    lines = [ln.strip() for ln in response.strip().splitlines() if ln.strip()]
    text = ""
    correct = ""
    options: list[str] = []
    for line in lines:
        if line.upper().startswith("CORRECT:"):
            correct = line[8:].strip()
        elif line and line[0] in "ABCDabcd" and ". " in line:
            options.append(line.split(". ", 1)[1].strip())
        elif not text and line and not line.upper().startswith("CORRECT:"):
            text = line
    return text, correct, options
