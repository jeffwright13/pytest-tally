import json
from typing import Any, Dict


def human_time_duration(seconds):
    # Credit to borgstrom: https://gist.github.com/borgstrom/936ca741e885a1438c374824efb038b3
    TIME_DURATION_UNITS = (
        ("week", 60 * 60 * 24 * 7),
        ("day", 60 * 60 * 24),
        ("hour", 60 * 60),
        ("min", 60),
        ("sec", 1),
    )

    if seconds == 0:
        return "inf"
    parts = []
    for unit, div in TIME_DURATION_UNITS:
        amount, seconds = divmod(int(seconds), div)
        if amount > 0:
            parts.append(f'{amount} {unit}{"" if amount == 1 else "s"}')
    return ", ".join(parts)


def cleanup_unserializable(d: Dict[str, Any]) -> Dict[str, Any]:
    # Credit to https://github.com/pytest-dev/pytest-reportlog
    """Return new dict with entries that are not json serializable by their str()."""
    result = {}
    for k, v in d.items():
        try:
            json.dumps({k: v})
        except TypeError:
            v = str(v)
        result[k] = v
    return result
