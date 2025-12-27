"""Conflict detection between mods."""

import sqlite3
from dataclasses import dataclass, field

# Resource types by severity
HIGH_SEVERITY_TYPES = {"CASPart", "Geometry", "DDS", "PNG", "DST"}
MEDIUM_SEVERITY_TYPES = {"Tuning", "SimData", "CombinedTuning"}
LOW_SEVERITY_TYPES = {"StringTable", "Thumbnail", "ThumbnailAlt"}


@dataclass
class ConflictCluster:
    """A cluster of mods that share conflicting resources."""

    mods: list[str] = field(default_factory=list)
    resources: list[tuple[int, int, int]] = field(default_factory=list)  # (type, group, instance)
    resource_types: set[str] = field(default_factory=set)
    severity: str = "low"


def determine_severity(resource_types: set[str]) -> str:
    """Determine conflict severity based on resource types."""
    if resource_types & HIGH_SEVERITY_TYPES:
        return "high"
    if resource_types & MEDIUM_SEVERITY_TYPES:
        return "medium"
    return "low"


def find_conflicts(conn: sqlite3.Connection) -> list[ConflictCluster]:
    """Find all conflict clusters.

    A conflict is when multiple mods contain resources with the same TGI.
    Conflicts are grouped into clusters using connected components.

    Args:
        conn: Database connection

    Returns:
        List of ConflictCluster objects
    """
    # Find all TGI collisions
    cursor = conn.execute("""
        SELECT
            r.type_id, r.group_id, r.instance_id, r.type_name,
            GROUP_CONCAT(m.path) as mod_paths
        FROM resources r
        JOIN mods m ON r.mod_id = m.id
        WHERE m.broken = 0
        GROUP BY r.type_id, r.group_id, r.instance_id
        HAVING COUNT(DISTINCT m.id) > 1
    """)

    # Build adjacency: mod -> set of mods it conflicts with
    adjacency: dict[str, set[str]] = {}
    # Track TGI info per mod pair
    mod_tgis: dict[str, list[tuple[int, int, int, str]]] = {}

    for row in cursor.fetchall():
        type_id, group_id, instance_id, type_name, mod_paths_str = row
        mod_paths = mod_paths_str.split(",")

        # Add edges between all conflicting mods
        for mod in mod_paths:
            if mod not in adjacency:
                adjacency[mod] = set()
            if mod not in mod_tgis:
                mod_tgis[mod] = []
            adjacency[mod].update(mod_paths)
            adjacency[mod].discard(mod)  # Remove self
            mod_tgis[mod].append((type_id, group_id, instance_id, type_name or "Unknown"))

    # Find connected components (clusters)
    visited = set()
    clusters = []

    def dfs(mod: str, cluster_mods: list[str]):
        if mod in visited:
            return
        visited.add(mod)
        cluster_mods.append(mod)
        for neighbor in adjacency.get(mod, []):
            dfs(neighbor, cluster_mods)

    for mod in adjacency:
        if mod not in visited:
            cluster_mods: list[str] = []
            dfs(mod, cluster_mods)

            if len(cluster_mods) > 1:
                # Collect all TGIs and types for this cluster
                all_tgis = set()
                all_types = set()
                for m in cluster_mods:
                    for tgi in mod_tgis.get(m, []):
                        all_tgis.add((tgi[0], tgi[1], tgi[2]))
                        all_types.add(tgi[3])

                cluster = ConflictCluster(
                    mods=sorted(cluster_mods),
                    resources=list(all_tgis),
                    resource_types=all_types,
                    severity=determine_severity(all_types),
                )
                clusters.append(cluster)

    # Sort by severity (high first)
    severity_order = {"high": 0, "medium": 1, "low": 2}
    clusters.sort(key=lambda c: (severity_order[c.severity], -len(c.mods)))

    return clusters
