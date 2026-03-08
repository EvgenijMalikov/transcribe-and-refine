"""
Small runtime helpers shared across entry-point modules.
"""

import sys


MIN_PYTHON = (3, 10)


def require_python_310() -> None:
    """Fail fast when the interpreter is older than Python 3.10."""
    if sys.version_info < MIN_PYTHON:
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        raise RuntimeError(
            f"Python 3.10 or newer is required. Current version: {current_version}."
        )
