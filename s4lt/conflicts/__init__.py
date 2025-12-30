"""Conflict detection for Sims 4 mods."""

from s4lt.conflicts.detector import (
    detect_conflicts,
    Conflict,
    ConflictReport,
    ConflictSeverity,
)

__all__ = [
    "detect_conflicts",
    "Conflict",
    "ConflictReport",
    "ConflictSeverity",
]
