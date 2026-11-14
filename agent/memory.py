import json
import re
from pathlib import Path

MEMORY_FILE = Path("memory.json")
EXCLUDE_PROJECT = None  # used by the evaluation to hide a project's own lessons

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "when", "not",
    "are", "was", "but", "has", "have", "its", "into", "than", "then",
}


def load() -> list:
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_episode(episode: dict) -> None:
    data = load()
    data.append(episode)
    MEMORY_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _words(text: str) -> set:
    found = re.findall(r"[a-z_]+", text.lower())
    return {w for w in found if len(w) >= 3 and w not in STOPWORDS}


def _searchable(ep: dict) -> str:
    return ep.get("failure_text", "") + " " + " ".join(ep.get("lessons", []))


def recall(query: str, limit: int = 3) -> list:
    q = _words(query)
    scored = [
        (len(q & _words(_searchable(ep))), ep)
        for ep in load()
        if ep.get("project") != EXCLUDE_PROJECT
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [ep for score, ep in scored[:limit] if score > 0]


def search_memory(query: str) -> str:
    """Search past episodes for similar bugs. Pass the error types and symptoms you see (for example 'IndexError off by one' or 'float rounding'), not function names. Returns lessons from up to 3 past cases."""
    hits = recall(query)
    if not hits:
        return "No similar past cases found."
    lines = []
    for ep in hits:
        status = "fixed" if ep["success"] else "NOT fixed"
        lessons = ep.get("lessons")
        if lessons:
            for lesson in lessons:
                lines.append(f"- Lesson from {ep['project']} ({status}): {lesson}")
        else:
            lines.append(f"- Past case in {ep['project']} ({status}): {ep['report'][:300]}")
    return "\n".join(lines)