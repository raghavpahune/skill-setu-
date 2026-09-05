import os
from typing import Any

def is_explicit_demo_mode(is_demo: bool | None = None) -> bool:
    if is_demo is True:
        return True
    if is_demo is False:
        return False
    env_mode = os.getenv("SKILLSETU_DATA_MODE", "").strip().lower()
    return env_mode in ("demo", "synthetic")

