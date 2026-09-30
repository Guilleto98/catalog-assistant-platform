"""Private permissions for local ADK runtime data used by the demo."""

import os
from pathlib import Path


def harden_adk_runtime_directory() -> None:
    runtime = Path(__file__).resolve().parent / ".adk"
    runtime.mkdir(mode=0o700, exist_ok=True)
    os.chmod(runtime, 0o700)
    for database in runtime.glob("*.db"):
        os.chmod(database, 0o600)
