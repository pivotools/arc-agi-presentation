"""
Data loading helpers for the blog.

Puzzle JSON and solution Python files live in blog/data/puzzles/
(relative to blog project root).
"""

import json
from pathlib import Path

# Blog project root (directory containing _quarto.yml); data/ is next to src/
_BLOG_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = _BLOG_ROOT / "data"

TIMELINE_PATH = DATA_DIR / "timeline.json"

PUZZLES_DIR = DATA_DIR / "puzzles"


def load_puzzle(puzzle_id: str) -> dict:
    """
    Load puzzle JSON by id (e.g. "45a5af55" -> data/puzzles/45a5af55.json).

    Returns:
        Dict with "train" (and optionally "test") keys.
    """
    path = PUZZLES_DIR / f"{puzzle_id}.json"
    return json.loads(path.read_text())


def get_solution_path(puzzle_id: str) -> Path:
    """
    Return path to solution Python file for a puzzle.

    Convention: {puzzle_id}.py in data/puzzles/.
    """
    return PUZZLES_DIR / f"{puzzle_id}.py"


def load_baseline_vs_interleaved() -> dict:
    """
    Load baseline vs interleaved thinking experiments from
    blog/data/baseline_vs_interleaved.json.

    Returns:
        Dict with "data" (list of records), "createdAt", "totalRecords".
    """
    path = DATA_DIR / "baseline_vs_interleaved.json"
    return json.loads(path.read_text())


def load_refinement() -> dict:
    """
    Load refinement experiments from blog/data/refinement.json.

    Returns:
        Dict with "data" (list of records), "createdAt", "totalRecords".
    """
    path = DATA_DIR / "refinement.json"
    return json.loads(path.read_text())


def load_timeline() -> dict:
    """
    Load timeline events from blog/data/timeline.json.

    Returns:
        Dict with "events" (list of dicts with name, date, placement, and text or test).
    """
    raw = json.loads(TIMELINE_PATH.read_text())
    if not isinstance(raw, dict):
        raise ValueError("timeline.json root must be an object")
    events = raw.get("events")
    if not isinstance(events, list):
        raise ValueError("timeline.json must contain an 'events' array")
    required = ("name", "date", "placement")
    for i, ev in enumerate(events):
        if not isinstance(ev, dict):
            raise ValueError(f"timeline events[{i}] must be an object")
        for k in required:
            if k not in ev:
                raise ValueError(f"timeline events[{i}] missing required key {k!r}")
        if "text" not in ev and "test" not in ev:
            raise ValueError(f"timeline events[{i}] must have 'text' or 'test'")
    return raw

