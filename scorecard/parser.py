import json
from pathlib import Path

import yaml


def load_spec(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Spec file not found: {path}")

    content = p.read_text(encoding="utf-8")

    if p.suffix in (".yaml", ".yml"):
        return yaml.safe_load(content)
    elif p.suffix == ".json":
        return json.loads(content)
    else:
        try:
            return yaml.safe_load(content)
        except Exception:
            return json.loads(content)
