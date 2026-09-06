import os
from typing import Any

def is_explicit_demo_mode(is_demo: bool | None = None) -> bool:
    if is_demo is True:
        return True
    if is_demo is False:
        return False
    env_mode = os.getenv("SKILLSETU_DATA_MODE", "").strip().lower()
    return env_mode in ("demo", "synthetic")
def is_demo_scheme_id(scheme_id: str | None = None) -> bool:
    if not scheme_id or not isinstance(scheme_id, str):
        return False
    return scheme_id.startswith("sch-demo-") or scheme_id.startswith("demo-")
