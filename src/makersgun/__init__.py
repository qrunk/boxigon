"""makersgun package re-exports for backwards compatibility.

This package contains the split implementations of the original
`src/makersgun.py`. Importers expecting `from src.makersgun import
MakersGun, Brick` will continue to work.
"""
from .core import MakersGun
from .brick import Brick

__all__ = ["MakersGun", "Brick"]
