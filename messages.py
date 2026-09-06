import json
from pathlib import Path


def load_messages(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)
