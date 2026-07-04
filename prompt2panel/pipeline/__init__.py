"""prompt2panel pipeline — the shared workflow every interface calls."""
from . import library                            # noqa: F401
from .core import Job, Result, prompt_to_panel  # noqa: F401
