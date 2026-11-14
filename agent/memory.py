import json
import re
from pathlib import Path

MEMORY_FILE = Path("memory.json")


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
    return set(re.findall(r"[a-z_]+", text.lower()))


def recall(query: str, limit: int = 3) -> list:
    q = _words(query)
    scored = [(len(q & _words(ep["failure_text"])), ep) for ep in load()]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [ep for score, ep in scored[:limit] if score > 0]


def search_memory(query: str) -> str:
    """Search past episodes for similar bugs. Pass a short description of the test failures. Returns up to 3 past cases and how they ended."""
    hits = recall(query)
    if not hits:
        return "No similar past cases found."
    lines = []
    for ep in hits:
        status = "fixed" if ep["success"] else "NOT fixed"
        lines.append(f"- Past case in {ep['project']} ({status}): {ep['report'][:400]}")
    return "\n".join(lines)