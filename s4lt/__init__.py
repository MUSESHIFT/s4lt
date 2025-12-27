"""S4LT: Sims 4 Linux Toolkit.

A native Linux toolkit for Sims 4 mod management.
"""

from s4lt.core import Package, Resource, DBPFError

__version__ = "0.1.0"

__all__ = [
    "Package",
    "Resource",
    "DBPFError",
    "__version__",
]
