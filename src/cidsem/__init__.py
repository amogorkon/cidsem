"""cidsem package initializer

Expose a simple entry point for local development: `process_text`.
Also exposes the Barkeep memory adapter (barkeep.remember / barkeep.recall).
"""

from .entrypoint import process_text
from . import barkeep

__all__ = ["process_text", "barkeep"]
